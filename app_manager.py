import os
from sys import exit
import shutil
import subprocess
import pickle
import re
import datetime
from getpass import getpass
from getpass import getuser

try:
    from simple_term_menu import TerminalMenu
except ImportError as e:
    print("\nError: Please install Termial Menu with 'python -m pip install simple_term_menu'\n")
    raise(e)

def ask_validate(prompt, regex):
    while True:
        print(prompt)
        response = str(input())
        if re.search(regex, response):
            break
        else:
            print("Invalid response/n  Follow convention " + regex)

    return response

def choose_validate(prompt, true_regex, false_regex):
    ret = None    
    while True:
        print(prompt)
        response = str(input())
        if re.search(true_regex, response):
            ret = True
            break
        if re.search(false_regex, response):
            ret = False
            break
        else:
            print("Invalid response/n  Follow conventions " + true_regex + " OR " + false_regex)

    return ret

class app_manifest:
    def __init__(self):

        if not getuser() == 'steam':
            print("Error: Must be user 'steam' to manage SteamCMD applications. You are {}".format(getuser()))
            exit(-1)

        self.data = None
        self.filename = "app_manifest"

        self.valid = self.load()
        self.modified = False

    # opens the manifest and unpickles it
    # returns sucsess
    def load(self):
        if os.path.isfile(self.filename):
            inf = open(self.filename, 'rb')
            self.data = pickle.load(inf)
            inf.close()
            return True
        else:
            # No manifest
            print("Manifest not found")
            self.data = {}
            return False

    # pickles the manifest and saves it to disk
    def save(self):
        outf = open(self.filename, 'wb')
        pickle.dump(self.data, outf)
        outf.close()
        self.modified = False
        return True

    def newApp(self, name, app_id, anon, args):
        if os.path.exists('/home/steam/' + name + '/'):
            if not confirm("Existing directory '"+name+"' found. Continue anyway?"):
                #cancel
                return
        else:
            os.mkdir('/home/steam/' + name + '/')
        if args is None:
            args = []
        self.data[name] = {"id":app_id, "anon":anon, "args":args}

        self.modified = True
        return

    def createApp(self):
        print("Creating a new sever\n")
        
        name = ask_validate("Name server: ", "^[^*&%\s]+$")
        app_id = ask_validate("Enter app id: " , "^[0-9]{2,12}$")
        anon_menu = TerminalMenu(['No', 'Yes'], title="Is user verification required?")
        anon = anon_menu.show()

        args_menu = TerminalMenu(['No', 'Yes'], title="Additional Arguments?")
        args = None
        if args_menu.show():
            args = ask_validate("Enter arguments seperated by spaces: ", "^.+$").split()
            # enter args
        

        self.newApp(str(name), int(app_id), bool(anon), args)
        self.modified = True
        return

    def removeApp(self, name):
        del self.data[name]
        print("Server '{}' removed".format(name))
        self.modified = True
        return
        
    #util
    def printData(self):
        if len(self.data.keys()) == 0:
            # No server
            print("    No existing servers found  \n")
            return

        row_template = "{:>12} " * 4
        print("\nServers:\n")
        print(row_template.format("Name", "App ID", "Login", "Arguments"))
        for name, row in self.data.items():
            print(row_template.format(name, *map(str, row.values())))
        print('\n')
        return



    # Updaters
    def update(self, name):
        if not self.data[name]["anon"]:
            self.update_anon(name)
        else:
            self.update_login(name)

    def update_anon(self, name):
        appID = self.data[name]["id"]
        command = ["./steamcmd/steamcmd.sh", "+force_install_dir", "/home/steam/"+name+'/', "+login", "anonymous", "+app_update", str(appID), "validate", "+quit"]
        #Apply user defined arguments
        pos = 7
        for arg in self.data[name]["args"]:
            command.insert(pos, arg)
            pos += 1
        #print(command)
        print("Anonymously updating app {} : '{}'".format(appID, name))
        steamProc = subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=1)
        steamOut(steamProc)
        steamProc.wait()

    def update_login(self, name):
        appID = self.data[name]["id"]

        usrname = input("Enter Steam username: ")
        pswd = getpass("Enter Steam password: ")

        command = ["./steamcmd/steamcmd.sh", "+login", usrname, pswd, "+force_install_dir", "/home/steam/"+name+'/', "+app_update", str(appID), "validate", "+quit"]
        #print(command)
        print("Logging in and updating app {} : '{}'".format(appID, name))
        steamProc = subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=1)
        steamOut(steamProc)
        steamProc.wait()
    

def steamOut(steamProc):
    usr = getuser()
    for line in iter(steamProc.stdout.readline, b''):
        nline = str(line)[2:-3].strip()
        print("[{}][steamCMD]  {}".format(usr, nline))


def confirm(prompt):
    conf_menu = TerminalMenu(["Confirm", "Cancel"], title=prompt)
    val =  bool(conf_menu.show())
    return not val


if __name__ == "__main__":

    Manifest = app_manifest() 

    quit = False

    if not Manifest.valid:
        # No manifest menu
        badLoad_menu = TerminalMenu(["Add new server", "Exit"])
        selection = badLoad_menu.show()
        if selection == 0:
            Manifest.createApp()
        else:
            quit = True
            exit() # bad practice
    

    # Main Menu
    
    while not quit:
        Manifest.printData()

        main_menu = TerminalMenu(["Update a server", "New server", "Remove server", "Exit"], title="Main Menu")
        selection = main_menu.show()
        if selection == 0:
            # Pick server
            servers = list(Manifest.data.keys())
            server_menu = TerminalMenu(servers, title="Select server")
            server = server_menu.show()
            server = servers[server]
            if confirm("Update server " + server + "?"):
                Manifest.update(server)
        
        elif selection == 1:
            Manifest.createApp()
        elif selection == 2:
            #remove server
            servers = list(Manifest.data.keys())
            server_menu = TerminalMenu(servers, title="Select server to remove")
            server = server_menu.show()
            server = servers[server]

            if confirm("Remove server " + server + "?"):
                Manifest.removeApp(server)
                if confirm("Delete files on disk?"):
                    # Delete entire directory and contents
                    shutil.rmtree("/home/steam/{}/".format(server))
                    print("Files deleted")

        else:
            # exit
            quit = True


    # Exit
    Manifest.save()

