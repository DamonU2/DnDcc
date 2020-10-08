import os

from cs50 import SQL
from flask import Flask, redirect, render_template, request, session, flash
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from tempfile import mkdtemp

from helpers import login_required, dice_roll, char_required

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

#Calculate ability modifiers function
def mod(ability):
    return (ability-10)//2

app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Load database
db = SQL("sqlite:///DnDcc.db")

@app.route("/")
@login_required
def index():
    userid = session["userid"]
    char = []
    # Get characters from db
    rows = db.execute("SELECT * FROM characters WHERE userid = :userid", userid=userid)
    # Redirect to character creation page if no characters exist
    if len(rows) == 0:
        return render_template("new_character.html")
    else:
        # Create list of dicts to pass to index.html
        for row in rows:
            name = row["name"]
            clss = row["class"]
            level = row["level"]
            charid = row["charid"]
            line = {"name": name, "class": clss, "level": level, "charid": charid}
            char.append(line)
        # Pass info to index and render it
        return render_template("index.html", char=char)

@app.route("/login", methods = ["GET", "POST"])
def login():
    session.clear()
    if request.method == "POST":
        # Check for valid info
        if not request.form.get("username"):
            flash("You must provide a username")
            return render_template("login.html")
        elif not request.form.get("password"):
            flash("Please provide your password")
            return render_template("login.html")
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash("Username and/or password invalid")
            return render_template("login.html")
        else:
            # Set user
            session["userid"] = rows[0]["userid"]
            # Redirect user to home page
            return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    # Clear session
    session.clear()

    # Redirect to login
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Check for username and matching passwords
        if not request.form.get("username"):
            flash("You must enter a username")
            return render_template("register.html")
        elif not request.form.get("password"):
            flash("You must enter a password")
            return render_template("register.html")
        elif request.form.get("password") != request.form.get("confirmation"):
            flash("Passwords do not match")
            return render_template("register.html")
        else:
            # Check if username is already in the db
            username = request.form.get("username")
            r = db.execute("SELECT * FROM users WHERE username = :username", username=username)
            if len(r) > 0:
                flash("Username is already taken")
                return render_template("register.html")
            else:
                # Otherwise hash the password, and store username and password in db
                hash = generate_password_hash(request.form.get("password"))
                # Enter username and hash into db
                db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, hash)
                id = db.execute("SELECT userid FROM users WHERE username = :username", username=username)
                session["userid"] = int(id[0]["userid"])
                # Send alert and return go to index
                flash("Registered")
                return redirect("/")
    else:
                return render_template("register.html")

@app.route("/new_character", methods=["GET", "POST"])
@login_required
def new_character():
    # Display page if method is get
    if request.method == "GET":
        return render_template("new_character.html")
    else:
        # Check that name is entered
        if not request.form.get("name"):
            flash("Please choose a name")
            return render_template("new_character.html")
        else:
            userid = session["userid"]
            name = request.form.get("name")
            # Check if name is already used
            names = db.execute("SELECT name FROM characters WHERE name = :name AND userid = :userid", name=name, userid=userid)
            if len(names) > 0:
                flash("Name cannot be the same as another character")
                return render_template("new_character.html")
            # Load form data and pass to database
            clss = request.form.get("class")
            level = request.form.get("level")
            strn = request.form.get("str")
            dex = request.form.get("dex")
            con = request.form.get("con")
            intl = request.form.get("int")
            wis = request.form.get("wis")
            cha = request.form.get("cha")
            db.execute("INSERT INTO characters (userid, name, level, class) VALUES (?, ?, ?, ?)", userid, name, level, clss)
            # Get generated character ID
            cid = db.execute("SELECT charid FROM characters WHERE name = :name AND userid = :userid", name=name, userid=userid)
            charid = int(cid[0]["charid"])
            session["charid"] = charid
            # Insert ability scores into database
            db.execute("INSERT INTO abilities (charid, str, dex, con, int, wis, cha) VALUES (?, ?, ?, ?, ?, ?, ?)", charid, strn, dex, con, intl, wis, cha)
            flash("Created!")
            return redirect ("/character")

@app.route("/update", methods=["GET", "POST"])
@login_required
@char_required
def update():
    # Display page if method is get
    if request.method == "GET":
        charid = session["charid"]
        row = db.execute("SELECT * FROM characters WHERE charid = :charid", charid=charid)
        level = int(row[0]["level"])
        rows = db.execute("SELECT * FROM abilities WHERE charid = :charid", charid=charid)
        # Generate ability list and level to pass to select menus
        strn = rows[0]["str"]
        dex = rows[0]["dex"]
        con = rows[0]["con"]
        intl = rows[0]["int"]
        wis = rows[0]["wis"]
        cha = rows[0]["cha"]
        atts = {"str": strn, "dex": dex, "con": con, "int": intl, "wis": wis, "cha": cha}
        return render_template("update.html", atts=atts, level=level)
    else:
        # Collect info and update databases
        charid = session["charid"]
        level = request.form.get("level")
        strn = request.form.get("str")
        dex = request.form.get("dex")
        con = request.form.get("con")
        intl = request.form.get("int")
        wis = request.form.get("wis")
        cha = request.form.get("cha")
        db.execute("UPDATE characters SET level = :level WHERE charid = :charid", level=level, charid=charid)
        db.execute("UPDATE abilities SET str = :strn, dex = :dex, con = :con, int = :intl, wis = :wis, cha = :cha WHERE charid = :charid", strn=strn, dex=dex, con=con, intl=intl, wis=wis, cha=cha, charid=charid)
        flash("Updated!")
        return redirect ("/character")

@app.route("/spell", methods=["GET", "POST"])
@login_required
@char_required
def spell():
    # Display page if method is get
    if request.method == "GET":
        return render_template("spell.html")
    else:
        # Check that a spell name is entered
        if not request.form.get("spell"):
            flash("Please choose a spell name")
            return render_template("spell.html")
        else:
            charid = session["charid"]
            # Make sure spell name is unique
            spell = request.form.get("spell")
            names = db.execute("SELECT spell FROM spells WHERE spell = :spell AND charid = :charid", spell=spell, charid=charid)
            if len(names) > 0:
                flash("Spell name must be unique for character")
                return render_template("spell.html")
            # Collect info and create database entry
            dicenum = request.form.get("dicenum")
            dicetype = request.form.get("dicetype")
            damtype = request.form.get("damtype")
            db.execute("INSERT INTO spells (charid, spell, dicenum, dicetype, damtype) VALUES (?, ?, ?, ?, ?)", charid, spell, dicenum, dicetype, damtype)
            flash("Created!")
            return redirect("/character")

@app.route("/weapon", methods=["GET", "POST"])
@login_required
@char_required
def weapon():
    # Display page if method is get
    if request.method == "GET":
        return render_template("weapon.html")
    else:
        # Check for weapon name
        if not request.form.get("weapon"):
            flash("Please choose a weapon name")
            return render_template("weapon.html")
        else:
            charid = session["charid"]
            weapon = request.form.get("weapon")
            # Make sure weapon name is unique for character
            names = db.execute("SELECT weapon FROM weapons WHERE weapon = :weapon AND charid = :charid", weapon=weapon, charid=charid)
            if len(names) > 0:
                flash("Weapon name must be unique for character")
                return render_template("weapon.html")
            # Collect data and insert in database
            bonus = request.form.get("bonus")
            prof = request.form.get("prof")
            ability = request.form.get("ability")
            dicenum = request.form.get("dicenum")
            dicetype = request.form.get("dicetype")
            damtype = request.form.get("damtype")
            db.execute("INSERT INTO weapons (charid, weapon, bonus, prof, ability, dicenum, dicetype, damtype) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", charid, weapon, bonus, prof, ability, dicenum, dicetype, damtype)
            flash("Created!")
            return redirect("/character")

@app.route("/character", methods=["GET", "POST"])
@login_required
def character():
    # If page is reached by POST from index, set character id to selected character
    if request.method == "POST":
        name = request.form.get("pick")
        row = db.execute("SELECT charid FROM characters WHERE userid = :userid AND name = :name", userid=session["userid"], name=name)
        session["charid"] = int(row[0]["charid"])
    charid = session["charid"]
    # Begin collecting data from database to populate page
    row = db.execute("SELECT * FROM characters WHERE charid = :charid", charid=charid)
    name = row[0]["name"]
    clss = row[0]["class"]
    level = int(row[0]["level"])
    # Proficiency calculation
    session["prof"] = ((level -1)//4) + 2
    # Character info to render
    char = {"charid": charid, "name": name, "class": clss, "level": level}
    rows = db.execute("SELECT * FROM abilities WHERE charid = :charid", charid=charid)
    # Calculates saving throw modifiers, and sets them as session data
    session["st_str"] = mod(rows[0]["str"])
    session["st_dex"] = mod(rows[0]["dex"])
    session["st_con"] = mod(rows[0]["con"])
    session["st_int"] = mod(rows[0]["int"])
    session["st_wis"] = mod(rows[0]["wis"])
    session["st_cha"] = mod(rows[0]["cha"])
    # Sets saving throw proficiencies
    if clss == "Barbarian" or clss == "Fighter":
        session["st_str"] = session["st_str"] + session["prof"]
        session["st_con"] = session["st_con"] + session["prof"]
    elif clss == "Bard":
        session["st_dex"] = session["st_dex"] + session["prof"]
        session["st_cha"] = session["st_cha"] + session["prof"]
    elif clss == "Cleric" or clss == "Paladin" or clss == "Warlock":
        session["st_wis"] = session["st_wis"] + session["prof"]
        session["st_cha"] = session["st_cha"] + session["prof"]
    elif clss == "Druid" or clss == "Wizard":
        session["st_int"] = session["st_int"] + session["prof"]
        session["st_wis"] = session["st_wis"] + session["prof"]
    elif clss == "Monk" or clss == "Ranger":
        session["st_dex"] = session["st_dex"] + session["prof"]
        session["st_str"] = session["st_str"] + session["prof"]
    elif clss == "Rogue":
        session["st_dex"] = session["st_dex"] + session["prof"]
        session["st_int"] = session["st_int"] + session["prof"]
    else:
        session["st_con"] = session["st_con"] + session["prof"]
        session["st_cha"] = session["st_cha"] + session["prof"]

    # Calculates ability modifiers, and sets them as session data
    session["str_mod"] = mod(rows[0]["str"])
    session["dex_mod"] = mod(rows[0]["dex"])
    session["con_mod"] = mod(rows[0]["con"])
    session["int_mod"] = mod(rows[0]["int"])
    session["wis_mod"] = mod(rows[0]["wis"])
    session["cha_mod"] = mod(rows[0]["cha"])

    # Determines spell ability modifier based on class
    if clss == "Bard" or clss == "Sorcerer" or clss == "Paladin" or clss == "Warlock":
        session["sp_ab"] = session["cha_mod"]
    elif clss == "Wizard" or clss == "Fighter" or clss == "Rogue":
        session["sp_ab"] = session["int_mod"]
    else:
        session["sp_ab"] = session["wis_mod"]

    # Collect ability info
    strn = rows[0]["str"]
    dex = rows[0]["dex"]
    con = rows[0]["con"]
    intl = rows[0]["int"]
    wis = rows[0]["wis"]
    cha = rows[0]["cha"]
    atts = {"str": strn, "dex": dex, "con": con, "int": intl, "wis": wis, "cha": cha}
    w = db.execute("SELECT * FROM weapons WHERE charid = :charid", charid=charid)

    # Collect weapon info
    weaps = []
    for row in w:
        weapon = row["weapon"]
        prof = row["prof"]
        ability = row["ability"]
        dicenum = int(row["dicenum"])
        dicetype = int(row["dicetype"])
        bonus = int(row["bonus"])
        damtype = row["damtype"]
        weap = {"weapon": weapon, "prof": prof, "ability": ability, "dicenum": dicenum, "dicetype": dicetype, "bonus": bonus, "damtype": damtype}
        weaps.append(weap)

    # Collect spell info
    s = db.execute("SELECT * FROM spells WHERE charid = :charid", charid=charid)
    spells = []
    for row in s:
        spell = row["spell"]
        dicenum = int(row["dicenum"])
        dicetype = int(row["dicetype"])
        damtype = row["damtype"]
        spell = {"spell": spell, "dicenum": dicenum, "dicetype": dicetype, "damtype": damtype}
        spells.append(spell)
    # Pass info to index and render it
    return render_template("character.html", char=char, atts=atts, weaps=weaps, spells=spells)

@app.route("/combat")
@login_required
def combat():
    charid = session["charid"]

    # Collect weapon info
    w = db.execute("SELECT * FROM weapons WHERE charid = :charid", charid=charid)
    weaps = []
    for row in w:
        weapon = row["weapon"]
        prof = row["prof"]
        ability = row["ability"]
        dicenum = int(row["dicenum"])
        dicetype = int(row["dicetype"])
        bonus = int(row["bonus"])
        damtype = row["damtype"]
        weap = {"weapon": weapon, "prof": prof, "ability": ability, "dicenum": dicenum, "dicetype": dicetype, "bonus": bonus, "damtype": damtype}
        weaps.append(weap)

    # Collect spell info
    s = db.execute("SELECT * FROM spells WHERE charid = :charid", charid=charid)
    spells = []
    for row in s:
        spell = row["spell"]
        dicenum = int(row["dicenum"])
        dicetype = int(row["dicetype"])
        damtype = row["damtype"]
        spell = {"spell": spell, "dicenum": dicenum, "dicetype": dicetype, "damtype": damtype}
        spells.append(spell)

    # Pass info to index and render it
    return render_template("combat.html", weaps=weaps, spells=spells)

# Saving throw function
@app.route("/saving_throw", methods=["POST"])
@char_required
def saving_throw():
    # Get saving throw modifier based on which button was clicked
    att = request.form.get("saving_throw")
    # Roll 20 sided die
    r = dice_roll(20)
    # Flash roll info in alert
    flash("You rolled {}, plus {}, gives {}" .format(r, session[att], session[att] + r))
    return redirect("/combat")

# Initiative function
@app.route("/init", methods=["POST"])
@char_required
def init():
    # Get dexterity modifier
    dex_mod = session["dex_mod"]
    # Roll 20 sided die
    r = dice_roll(20)
    # Flash roll info in alert
    flash("You rolled {}, plus {}, gives initiative of {}" .format(r, dex_mod, dex_mod + r))
    return redirect("/combat")

# Weapon attack functio
@app.route("/weapon_attack", methods=["POST"])
@char_required
def weapon_attack():
    charid = session["charid"]
    # Get weapon stats
    weapon = request.form.get("weapon_attack")
    row = db.execute("SELECT * FROM weapons WHERE charid = :charid AND weapon = :weapon", charid=charid, weapon=weapon)
    # Set proficiency bonus
    prof = session["prof"] * row[0]["prof"]
    # Set variables for attack roll
    att = session[row[0]["ability"]]
    dicenum = row[0]["dicenum"]
    dicetype = row[0]["dicetype"]
    bonus = row[0]["bonus"]
    damtype = row[0]["damtype"]
    damage = 0
    # Roll 20 sided die
    r = dice_roll(20)
    # Special scenario if 20 or 1 are rolled
    if r == 20:
        # Damage dice are doubled for a critical hit
        dicenum = dicenum * 2
        # Roll damage dice dicenum times
        for i in range(0, dicenum):
            damage += dice_roll(dicetype)
        # Add bonus and attribute bonus to damage
        damage = damage + bonus + att
        # Display roll info in alert
        flash("Critical Hit for {} {} damage!".format(damage, damtype))
        return redirect("/combat")
    elif r == 1:
        # If a one is rolled, no further calculations are necessary
        flash("1! Miss!")
        return redirect("/combat")
    else:
        # Roll damage die dicenum times
        for i in range(0, dicenum):
            damage += dice_roll(dicetype)
        # Add bonuses to damage
        damage = damage + bonus + att
        # Display roll info
        flash("Attack roll of {}, plus {} is {}. If the attack hits, it does {} {} damage".format(r, bonus + att + prof, r + bonus + att + prof, damage, damtype))
        return redirect("/combat")

# Spell attack function
@app.route("/spell_attack", methods=["POST"])
@char_required
def spell_attack():
    # Set spell info variables
    charid = session["charid"]
    spell = request.form.get("spell_attack")
    ab = session["sp_ab"]
    prof = session["prof"]
    row = db.execute("SELECT * FROM spells WHERE charid = :charid AND spell = :spell", charid=charid, spell=spell)
    dicenum = row[0]["dicenum"]
    dicetype = row[0]["dicetype"]
    damtype = row[0]["damtype"]
    damage = 0
    # Roll 20 sided dice
    r = dice_roll(20)
    # Special scenario if 20 or 1 are rolled
    if r == 20:
        # Damage dice are doubled for a critical hit
        dicenum = dicenum * 2
        # Roll damage die dicenum times
        for i in range(0, dicenum):
            damage += dice_roll(dicetype)
        # Display roll info
        flash("Critical Hit for {} {} damage!".format(damage, damtype))
        return redirect("/combat")
    elif r == 1:
        # If a one is rolled, no further calculations are necessary
        flash("1! Miss!")
        return redirect("/combat")
    else:
        # Roll damage die dicenum times
        for i in range(0, dicenum):
            damage += dice_roll(dicetype)
        # Display roll info
        flash("Attack roll of {}, plus {} is {}. If the attack hits, it does {} {} damage".format(r, ab + prof, r + ab + prof, damage, damtype))
        return redirect("/combat")

@app.route("/delete_weapon", methods=["POST"])
@char_required
def delete_weapon():
    # Get weapon name and remove it's entry from database
    weapon = request.form.get("delete_weapon")
    db.execute("DELETE FROM weapons WHERE weapon = :weapon AND charid = :charid", weapon=weapon, charid=session["charid"])
    return redirect("/character")

@app.route("/delete_spell", methods=["POST"])
@char_required
def delete_spell():
    # Get spell name and remove it's entry from database
    spell = request.form.get("delete_spell")
    db.execute("DELETE FROM spells WHERE spell = :spell AND charid = :charid", spell=spell, charid=session["charid"])
    return redirect("/character")

@app.route("/delete_character", methods=["POST"])
@login_required
def delete_character():
    # Get character name and remove it's entry from database
    charid = request.form.get("delete_character")
    db.execute("DELETE FROM characters WHERE userid = :userid AND charid = :charid", userid=session["userid"], charid=charid)
    db.execute("DELETE FROM abilities WHERE charid = :charid", charid=charid)
    db.execute("DELETE FROM weapons WHERE charid = :charid", charid=charid)
    db.execute("DELETE FROM spells WHERE charid = :charid", charid=charid)
    return redirect("/")

if __name__ == '__main__':
    app.run(debug=True)