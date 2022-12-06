import os

def get_build_root():
    return os.path.dirname(os.path.abspath(__file__))

def get_build_folder(name):
    build_folder = os.path.join(get_build_root(), name)
    if not os.path.exists(build_folder):
        os.mkdir(build_folder)
    return build_folder

def get_build_var(name):
    var_file_path = os.path.join(get_build_folder(".vars"), name)
    if not os.path.exists(var_file_path):
        print("Could not find var %s at %s" % (name, var_file_path))
        print("Are you sure you ran the previous scripts?")
        sys.exit(1)
    var_file = open(var_file_path)
    var = var_file.read()
    var_file.close()
    print("%s -> %s" % (name, var))
    return var

def get_config_path():
    return os.path.realpath(os.path.join(get_build_root(), "config.json"))
