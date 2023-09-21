#!/usr/local/bin/python

import os

flag = os.getenv("FLAG")

if input("Do you want the flag?").lower().startswith("y"):
    print(flag)
print("bye!")
