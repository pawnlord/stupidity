import json
import os
import sys
import time
import hashlib

if not os.path.exists(".stupidity"):
    os.makedirs(".stupidity")
if not os.path.exists(".stupidity/stpd.json"):
    with open(".stupidity/stpd.json", 'w') as file:
        file.write('{}')

def getval(header, val, d, default = ""):
    if header in d.keys():
        headerVal = d[header]
        if val in headerVal.keys():
            return headerVal[val]
    else: 
        d[header] = {}
    d[header][val] = default
    return default
def getdict(header, config):
    if header in config.keys():
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
    file.seek(0)
    return sha1

class CommitNode:
    def __init__(self, name, data, parent=None, current=None):
        self.parent = parent
        self.name = name
        self.children = {}
        self.current = None
        for key, node in data.items():
            self.children[key] = CommitNode(key, node, self)
            if key == current:
                self.current = self.children[key]
            elif self.children[key].current != None:
                self.current = self.children[key].current
    def getlist(self):
        data = {}
        for key, child in self.children.items():
            data[key] = child.getlist()
            ###
        return data
class CommitTree: 
    def __init__(self, current, data):
        self.data = data
        self.current = current
        self.root = CommitNode("root", data, None, current)
        self.currentNode = self.root
        if self.currentNode.current != None:
            self.currentNode = self.currentNode.current        
    def add_hash(self, hash):
        if not hash in self.currentNode.children.keys(): 
            self.current = hash
            self.currentNode.children[hash] = CommitNode(hash, {}, self.currentNode)
        self.currentNode = self.currentNode.children[hash]
    def encode(self):
        return self.root.getlist()
class FileData:
    def __init__(self, data):
        self.data = data
        self.tree = CommitTree(data["hash"] if "hash" in data.keys() else "", data["tree"] if "tree" in data.keys() else {})
        self.time_added = data["time_added"] if "time_added" in data.keys() else str(time.time())
    def clean_up(self):
        self.data["tree"] = self.tree.encode()
    def add_file(self, file, hash = None):
        if not hash:
            hash =  get_file_hash(file).hexdigest();
        
        self.tree.add_hash(hash)
        self.data =  {
            "time_added" : str(time.time()) if not "time_added" in self.data.keys() else self.data["time_added"],
            "time_modified" : str(time.time()),
            "hash" : hash
        }
            

class StupidityRepo:
    def __init__(self):

        with open('.stupidity/stpd.json', 'r') as infofile:
            self.info = json.load(infofile)

        self.tracked_filenames = getval("FileInfo", "tracked", self.info,[])
        if not "Files" in self.info.keys():
            self.info["Files"] = {} 
        self.tracked_files = {name:FileData(getdict(name, getdict("Files", self.info))) for name in self.tracked_filenames} 
        print(self.tracked_files)
        
    
    def getnext(self, args, idx, verbose=True):
        idx, arg, options = getnext(args, idx, verbose)
        self.process_options(options)
        
        return idx, arg
    
    def process_options(self, options):
        pass
    
    def close(self):
        for filename, file in self.tracked_files.items():
            file.clean_up()
            self.info["Files"][filename] = file.data
        self.info["FileInfo"]["tracked"] = self.tracked_filenames
        with open('.stupidity/stpd.json', 'w') as infofile:
            json.dump(self.info, infofile)
    def add_file(self, filename : str, file):
        # add data to commite file
        path = ".stupidity/{}".format(get_file_hash(file).hexdigest())
        print(get_file_hash(file).hexdigest())
        os.makedirs(path)
        with open(path + "/" + filename, "w+") as commit_file:
            data = file.read()
            commit_file.write(data)
        file.seek(0)
        

    def add_file_data(self, filename : str, file ):
        if not filename in self.tracked_filenames:
            self.tracked_filenames.append(filename)
            if filename in self.tracked_files.keys():
                self.tracked_files[filename].add_file(file)
            else:
                self.tracked_files[filename] = FileData({ 
                        "time_added" : str(time.time()),
                        "time_modified" : str(time.time()),
                        "hash" : get_file_hash(file).hexdigest(),
                    })
            self.add_file(filename, file)
        else:
            file_data = self.tracked_files[filename]
            hash = get_file_hash(file).hexdigest()
            if hash != file_data.data["hash"]:
                file_data.add_file(file, hash)
                self.add_file(filename, file)
            

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
                repo.add_file_data(filename, file)
            idx, filename = repo.getnext(args, idx, verbose=False)
    print(repo.tracked_files)
    print(repo.tracked_filenames)
    repo.close()
if __name__ == "__main__":
    argv = sys.argv[:]
    if argv[0] != "stpd" or argv[0] != "stpd.py":
        argv = argv[1:]
    main(argv)