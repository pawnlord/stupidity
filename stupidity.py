import configparser
import os
import sys
import time
import hashlib

if not os.path.exists(".stupidity"):
    os.makedirs(".stupidity")
if not os.path.exists(".stupidity/stpd.cfg"):
    with open(".stupidity/stpd.cfg", 'w'):
        pass

def getval(header, val, config : configparser.ConfigParser, default = ""):
    if config.has_section(header):
        headerVal = config[header]
        if val in headerVal.keys():
            return headerVal[val]
    else: 
        config[header] = {}
    config[header][val] = default
    return default
def getval(header, val, d : dict, default = ""):
    if header in d.keys():
        headerVal = d[header]
        if val in headerVal.keys():
            return headerVal[val]
    else: 
        d[header] = {}
    d[header][val] = default
    return default
def getdict(header, config):
    if config.has_section(header):
        return  config[header]
    return {}

def getnext(args, idx, verbose=True):
    found_next = False
    options = []
    while not found_next:
        found_next = True
        idx += 1;
        if len(args) <= idx:
            if verbose:
                print("Expected more arguments. Use -h/--help for more")
            return (idx, None, options)
        if args[idx][0] == '-':
            found_next = False
            options.append(args[idx])
            continue
        else:
            return (idx, args[idx], options)

def get_file_hash(file, buf_size=2048):
    sha1 = hashlib.sha1()
    data = file.read(buf_size)
    while data:
        sha1.update(data.encode('utf-8'))
        data = file.read(buf_size)
    return sha1
class StupidityRepo:
    def __init__(self):
        self.config = configparser.ConfigParser()

        with open('.stupidity/stpd.cfg', 'r') as configfile:
            self.config.read_file(configfile)

        self.tracked_filenames = getval("FILES", "tracked", self.config).split(',')
        self.tracked_files = {"FILE:" + name:getdict("FILE:" + name, self.config) for name in self.tracked_filenames} 
        print(self.tracked_files)
        
    
    def getnext(self, args, idx, verbose=True):
        idx, arg, options = getnext(args, idx, verbose)
        self.process_options(options)
        
        return idx, arg
    
    def process_options(self, options):
        pass
    
    def close(self):
        self.config["FILES"]["tracked"] = ",".join(self.tracked_filenames)
        with open('.stupidity/stpd.cfg', 'w') as configfile:
            self.config.write(configfile)
    
    def add_file(self, filename : str, file ):
        if not filename in self.tracked_filenames:
            self.tracked_filenames.append(filename)
        
            self.tracked_files["FILE:" + filename] = {
                            "time_added" : str(time.time()),
                            "time_modified" : str(time.time()),
                            "hash" : get_file_hash(file).hexdigest()
                        }
            self.config["FILE:" + filename] = self.tracked_files["FILE:" + filename]
        
        else:
            file_data = self.tracked_files["FILE:" + filename]
            hash = get_file_hash(file).hexdigest()
        
            if hash != file_data["hash"]:
                self.tracked_files["FILE:" + filename] = {
                                "time_added" : getval("FILE:" + filename, "time_added", self.tracked_files, str(time.time())),
                                "time_modified" : str(time.time()),
                                "hash" : get_file_hash(file).hexdigest()
                            }
                self.config["FILE:" + filename] = self.tracked_files["FILE:" + filename]


def main(args):
    print (args)
    repo = StupidityRepo()
    idx = -1
    idx, command = repo.getnext(args, idx)
    command = command.lower()
    print(command)
    if command == "add":
        idx, filenameRaw = repo.getnext(args, idx)
        filename = os.path.relpath(filenameRaw)

        while filename != None:
            if not os.path.exists(filename):
                print("[stupidity] {}: File/path does not exist".format(filename))
                exit()
            if not os.path.isfile(filename):
                print("[stupidity] {}: Not a file".format(filename))
                exit()
            with open(filename, 'r+') as file:
                repo.add_file(filename, file)
            idx, filename = repo.getnext(args, idx, verbose=False)
    print(repo.tracked_files)
    print(repo.tracked_filenames)
    repo.close()
if __name__ == "__main__":
    argv = sys.argv[:]
    if argv[0] != "stpd" or argv[0] != "stpd.py":
        argv = argv[1:]
    main(argv)