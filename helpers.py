import os
import random

from flask import redirect, render_template, request, session
from functools import wraps

# Make sure user is logged in
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("userid") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

# Make sure character is selected
def char_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("charid") is None:
            return redirect("/")
        return f(*args, **kwargs)
    return decorated_function

# Function for any diceroll
def dice_roll(dicetype):
    number = random.randint(1, dicetype)
    return number