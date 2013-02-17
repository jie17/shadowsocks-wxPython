
from distutils.core import setup
import py2exe
options = {"py2exe":  
            {   "compressed": 1,  
                "optimize": 2,  
                "bundle_files": 1, 
                "excludes": ['_ssl','doctest','pdb','unittest','difflib','inspect']
            }  
          }  
setup(     
    description = "shadowsocks-wxPython",  
    name = "shadowsocks",  
    options = options,  
    data_files=[("",["config.json",])],
    zipfile=None,  
    windows=[{"script": "shadowsocks-wxPython.py", "icon_resources": [(1, "icon.ico")] }],    
    )  