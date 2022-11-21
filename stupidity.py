import configparser
import os
import sys
import time
import hashlib

if not os.path.exists(".stupidity"):
    os.makedirs(".stupidity")
if not os.path.exists(".stupidity/stpd.inf"):
    with open(".stupidity/stpd.inf", 'w'):
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
    file.seek(0)
    return sha1

class CommitNode:
    def __init__(self, name, parent=None):
        self.parent = parent
        self.name = name
        self.children = []
    def add_child(self, node_name : str):
        self.children.append(CommitNode(node_name, self))
        return self.children[-1]
    def add_child_node(self, node):
        self.children.append(node)
        node.set_parent(self)
    def set_parent(self, node):
        self.parent = node

class CommitTree: 
    def __init__(self, current, data):
        self.edges = [(edge.split('|')[0], edge.split('|')[1]) if len(edge)>1 else (None,None) for edge in data.split(',')]
        self.tree_map = {}
        for edge in self.edges: # assume root first
            if edge[0] == None:
                continue
            if edge[0] == "":
                if edge[1] in self.tree_map.keys():
                    self.tree_map["root"] = self.tree_map[edge[1]]
                else:    
                    self.tree_map["root"] = CommitNode(edge[1], None)
            else:
                if not edge[0] in self.tree_map.keys():
                    self.tree_map[edge[0]] =  CommitNode(edge[0], None)
    
                if edge[1] in self.tree_map.keys():
                    self.tree_map[edge[0]].add_child_node(self.tree_map[edge[1]])
                else:
                    self.tree_map[edge[1]] = self.tree_map[edge[0]].add_child(edge[1])
        if not "root" in self.tree_map.keys():
            self.tree_map["root"] = CommitNode(current, None)
    def add_hash(self, current_hash, hash):
        if not current_hash in self.tree_map.keys():
            self.tree_map[current_hash] = CommitNode(current_hash, None)
        self.tree_map[current_hash].add_child(hash)
    def encode(self):
        repr_list = []
        for name, node in self.tree_map.items():
            if node == self.tree_map["root"] and name != "root":
                continue
            if name == "root":
                repr_list.append("|{}".format(node.name))
            for child in node.children:
                repr_list.append("{}|{}".format(node.name, child.name))
        return ",".join(repr_list)
class FileData:
    def __init__(self, data):
        self.data = data
        self.tree = CommitTree(data["hash"] if "hash" in data.keys() else "", data["tree"] if "tree" in data.keys() else "")
        self.time_added = data["time_added"] if "time_added" in data.keys() else str(time.time())
    def clean_up(self):
        self.data["tree"] = self.tree.encode()
    def add_file(self, file, hash = None):
        if not hash:
            hash =  get_file_hash(file).hexdigest();
        
        self.tree.add_hash(self.data["hash"], hash)
        self.data =  {
            "time_added" : str(time.time()) if not "time_added" in self.data.keys() else self.data["time_added"],
            "time_modified" : str(time.time()),
            "hash" : hash
        }
            

class StupidityRepo:
    def __init__(self):
        self.config = configparser.ConfigParser()

        with open('.stupidity/stpd.inf', 'r') as configfile:
            self.config.read_file(configfile)

        self.tracked_filenames = getval("FILES", "tracked", self.config).split(',')
        self.tracked_files = {"FILE:" + name:FileData(getdict("FILE:" + name, self.config)) for name in self.tracked_filenames} 
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
            self.config[filename] = file.data
        self.config["FILES"]["tracked"] = ",".join(self.tracked_filenames)
        with open('.stupidity/stpd.inf', 'w') as configfile:
            self.config.write(configfile)
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
            if "FILE:" + filename in self.tracked_files.keys():
                self.tracked_files["FILE:" + filename].add_file(file)
            else:
                self.tracked_files["FILE:" + filename] = FileData({ 
                        "time_added" : str(time.time()),
                        "time_modified" : str(time.time()),
                        "hash" : get_file_hash(file).hexdigest(),
                    })
            self.add_file(filename, file)
        else:
            file_data = self.tracked_files["FILE:" + filename]
            hash = get_file_hash(file).hexdigest()
            print(hash + "\n" + file_data.data["hash"])
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