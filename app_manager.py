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
            print("Error: Must be user 'steam' to manage SteamCMD applications. You are {}.".format(getuser()))
            exit(-1)

        self.data = None
        self.filename = ".SSM_manifest"

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


    def editArgs(self, name):
        cont = True
        while cont:
            args = self.data[name]['args']
            #print("Arguments for {}:\n  {}".format(name, args))
            argmenu = TerminalMenu(["Add argument", "Remove argument", "Rewrite all arguments", "Remove all arguments", "Exit"], title="Edit arguments for {}\n  {}".format(name, args))
            select = argmenu.show()

            if select == 0:
                # add arg
                nArgs = ask_validate("Enter new argument(s) seperated by spaces: \n  {}".format(args), "^.+$").split()
                self.data[name]['args'].extend(nArgs)
            elif select == 1:
                # rem arg
                if len(self.data[name]['args']) == 0:
                    print("No arguments to remove")
                else:
                    rem_menu = TerminalMenu(args+["Exit"], title="Remove argument:")
                    target = rem_menu.show()
                    if not target is None and not target == len(self.data[name]['args']):
                        # not cancel
                        if confirm("Remove argument '{}' for server {}?".format(args[target], name)):
                            self.data[name]['args'].remove(args[target])
            elif select == 2:
                # rewrite all
                if confirm("Delete all arguments and enter new set?"):
                    newArgs = ask_validate("Enter arguments seperated by spaces: \n  {}".format(args), "^.+$").split()
                    self.data[name]['args'] = newArgs
            elif select == 3:
                if confirm("Delete all {} arguments for {}?\n  {}".format(len(args), name, args)):
                    self.data[name]['args'] = []

            else: cont = False
            self.modified = True


    def editApp(self, name):
        items = ["{} : {}".format(k, v) for k, v in self.data[name].items()]
        items[1].replace("anon", "login")
        #items.insert(0, "name : {}".format(name))
        items.append("Exit")
        edit_menu = TerminalMenu(items, title="Edit properties for {}".format(name))
        prop = edit_menu.show()

        if prop == 0:
            #edit id
            print("{}:\n  id = {}".format(name, self.data[name]['id']))
            newid = ask_validate("Enter new app id: " , "^[0-9]{2,12}$")
            self.data[name]['id'] = newid
            print("{} app id set to {}".format(name, newid))
        elif prop == 1:
            #edit anon
            anon_menu = TerminalMenu(['No', 'Yes'], title="Is user verification required?")
            anon = anon_menu.show()
            self.data[name]['anon'] = bool(anon)
            print("{} app anonymity set to {}".format(name, bool(anon)))
        elif prop == 2:
            self.editArgs(name)
        else: return

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

        row_template = "{:<16} {:<12} {:<8} {:<24}"
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
        steamProc = subprocess.Popen(command, shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, bufsize=1)
        steamOut(steamProc)
        steamProc.wait()

    def update_login(self, name):
        appID = self.data[name]["id"]

        usrname = input("Enter Steam username: ")
        pswd = getpass("Enter Steam password: ")

        command = ["./steamcmd/steamcmd.sh", "+login", usrname, pswd, "+force_install_dir", "/home/steam/"+name+'/', "+app_update", str(appID), "validate", "+quit"]
        #print(command)
        print("Logging in and updating app {} : '{}'".format(appID, name))
        steamProc = subprocess.Popen(command, shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, bufsize=1)
        steamOut(steamProc)
        steamProc.wait()
    

# prints output
def steamOut(steamProc):
    usr = getuser()
    while steamProc.poll() is None:
        line = steamProc.stdout.readline()
        #line, err = steamProc.communicate()
        if line: 
            line = str(line).strip()
            print("[{}][steamCMD]  {}".format(usr, line))


def confirm(prompt):
    conf_menu = TerminalMenu(["Confirm", "Cancel"], title=prompt)
    val =  conf_menu.show()
    if val is None:
        return False
    return not bool(val)

def pickServer(Manifest):
    servers = list(Manifest.data.keys())
    server_menu = TerminalMenu(servers, title="Select server")
    server = server_menu.show()
    if not server is None:
        server = servers[server]
    return server


if __name__ == "__main__":

    Manifest = app_manifest() 

    quit = False

    ### Welcome message
    welcome = "\nWelcome to SteamServerManager, a wrapper for SteamCMD. \n  -- press 'q' or 'ESC' in any menu to go back --"
    print(welcome)
    
    if not Manifest.valid:
        # No manifest menu
        badLoad_menu = TerminalMenu(["Add new server", "Exit"], title="No manifest found")
        selection = badLoad_menu.show()
        if selection == 0:
            Manifest.createApp()
        else:
            quit = True
            exit() # bad practice
    

    # Main Menu
    
    while not quit:
        Manifest.printData()

        main_menu = TerminalMenu(["Update a server", "Edit server", "New server", "Remove server", "Exit"], title="Main Menu")
        selection = main_menu.show()
        if selection == 0:
            # Pick server
            server = pickServer(Manifest)
            if not server is None:
                if confirm("Update server " + server + "?"):
                    Manifest.update(server)
        elif selection == 1:
            #edit server
            server = pickServer(Manifest)
            if not server is None:
                Manifest.editApp(server)
        elif selection == 2:
            Manifest.createApp()
        elif selection == 3:
            #remove server
            servers = list(Manifest.data.keys()) + ["Cancel"]
            server_menu = TerminalMenu(servers, title="Select server to remove")
            server = server_menu.show()
            if not server is None and not server == len(servers) - 1:
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

