import sqlite3
import os, sys, time, datetime, random, string
import urllib.request, urllib.error
import configparser
from flask import Flask, request, session, redirect
from flask import render_template, g, flash, url_for
from contextlib import closing
from pxepagi import Pagi

pxeat_config = configparser.RawConfigParser()

try:
    pxeat_config.read('./pxeat.cfg')
except configparser.Error:
    print("Get configuration failed!")
 
general_opts = {}
pxefile_opts = {}
for option in pxeat_config.options('general'):
    try:
        general_opts[option] = pxeat_config.get('general', option)
        if general_opts[option] == -1:
            DebugPrint("skip: %s" % option)
    except:
        print("exception on %s!" % option)
        general_opts[option] = None

for option in pxeat_config.options('pxe_file'):
    try:
        pxefile_opts[option] = pxeat_config.get('pxe_file', option).split('\\n')
        if pxefile_opts[option] == -1:
            DebugPrint("skip: %s" % option)
    except:
        print("exception on %s!" % option)
        pxefile_opts[option] = None

SECRET_KEY = general_opts['secret_key']

postfix_kernelfn = '-0' 
postfix_initrdfn = '-1'

# Defaults
items = {}

app = Flask(__name__)
app.config.from_object(__name__)

def chk_input(chk_string, chk_type):

    if chk_type == 'pxe_title':
        if chk_string == '':
            raise ValueError("The title can not be empty!")
        return
    elif chk_type == 'file_path':
        if chk_string[0] != '/' or chk_string[-1] == '/':
            raise ValueError("Path format is invalid!")
        return
    elif chk_type == 'repo_url':
        chk_elements = chk_string.split('//')
        if chk_elements[1] == '':
            raise ValueError("The repository can not be empty!")
            return
        elif chk_elements[0] not in ['http:','https:']:
            raise ValueError("Invalid format!"+\
                             " (Only support http:// or https://)")
            return
    else:
        sys.exit("chk_type error!")

def prt_help():
    print("This is help info.:")


def grab_file(base_url, file_path, saved_file):

    file_url = base_url + file_path

    try:
        f = urllib.request.urlopen(file_url)
        local_file = open(saved_file, "wb")
        local_file.write(f.read())
        local_file.close()
    except urllib.error.HTTPError as e:
        return str(e.code) + " " + str(e.reason)
    except urllib.error.URLError as e:
        return str(e.reason)
    except urllib.error:
        return

def boot_opts_gen(opt_flag):
    if opt_flag == "vnc":
        return(general_opts['default_boot_opts'] + \
                         " vnc=1 vncpassword=" + \
                         general_opts['vnc_passwd'])
    elif opt_flag == "ssh":
        return(general_opts['default_boot_opts'] + \
                         " usessh=1 sshpassword=" + \
                         general_opts['ssh_passwd'])
    else:
        return(general_opts['default_boot_opts'])

def connect_db():
    return sqlite3.connect(general_opts['database'])

def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()

@app.route('/')
def form():
    return render_template('form.html')

app.jinja_env.globals['repo_kernel_default'] = general_opts['repo_kernel_default']
app.jinja_env.globals['repo_initrd_default'] = general_opts['repo_initrd_default']

@app.route('/history/', defaults={'page': 1})
@app.route('/history/page/<int:page>')
def history(page):
    count=50
    per_page=10
    pagination = Pagi(page, per_page, count)

    try:
        cur = g.db.execute('select pxe_title,\
                                repo_url,\
                                repo_kernel,\
                                repo_initrd,\
                                pxe_comment,\
                                unix_time,\
                                inst_flag from pxeitems order by id desc')
    except sqlite3.Error as e:
        return render_template('failed.html', failed_msg = "Database error: "+str(e))

    history_entries = [ dict(pxe_title=row[0], \
                    repo_url=row[1], \
                    repo_kernel=row[2], \
                    repo_initrd=row[3], \
                    pxe_comment=row[4], \
                    unix_time=datetime.datetime.fromtimestamp(int(row[5])), \
                    inst_flag=row[6]) \
            for row in cur.fetchall()[(page-1)*per_page:page*per_page]\
            ]

    if not history_entries and page != 1:
        #Shoud do something here other than pass or abort(404)
        pass

    return render_template('history.html',\
                            pagination=pagination,\
                            history_entries=history_entries)

@app.route('/about')
@app.route('/about/')
def about():
    return render_template('about.html')

# For the pagination
def url_for_other_page(page):
    args = request.view_args.copy()
    args['page'] = page
    return url_for(request.endpoint, **args)
app.jinja_env.globals['url_for_other_page'] = url_for_other_page

@app.route('/confirm', methods=['POST'])
def confirm_entry():
    
    #Input checking
    try:
        for x,y in [[request.form['pxe_title'],'pxe_title'], \
                  [request.form['repo_url'], 'repo_url'], \
                  [request.form['repo_kernel'], 'file_path'], \
                  [request.form['repo_initrd'], 'file_path']]:
            chk_input(x,y)
    except ValueError as e:
        flash(e.args[0],'error')
        return redirect(url_for('form'))
        #return render_template('form.html',ss="red")
        
    # Assign to the dictionary
    items['repo_kernel'] = request.form['repo_kernel']
    items['repo_url'] = request.form['repo_url']
    items['repo_initrd'] = request.form['repo_initrd']
    items['pxe_title'] = request.form['pxe_title']
    items['pxe_comment'] = request.form['pxe_comment']
    items['inst_flag'] = request.form['inst_method']

    # Generate a random string
    items['random_str'] = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))

    items['unix_time'] = ''

    # Show the entry which will be generated on the confirm page
    gen_format = ["menu label ^a - " + items['pxe_title'], \
              "kernel " + general_opts['loader_path'] + "[random]" + postfix_kernelfn, \
              "append initrd=" + general_opts['loader_path'] + "[random]" + postfix_initrdfn + " " + \
              boot_opts_gen(items['inst_flag']) + " " + \
              "install=" + items['repo_url']]

    return render_template('confirm.html', cfm_entries=items, cfm_fmt=gen_format)

@app.route('/add', methods=['POST'])
def add_entry():
    items['unix_time'] = str(int(time.time()))
    id_random = items['unix_time'] + items['random_str']

    for f_name,i in [[items['repo_kernel'], postfix_kernelfn],\
                     [items['repo_initrd'], postfix_initrdfn]]:
        ret = grab_file(items['repo_url'],\
                        f_name,\
                        general_opts['loader_path'] + id_random + i)
        if ret:
            return render_template('failed.html',\
                                    failed_msg = f_name + ": " + str(ret))
        else:
            pass

    # Save new entry to database

    try:
        g.db.execute('INSERT INTO pxeitems (\
                   pxe_title, \
                   repo_url, \
                   repo_kernel, \
                   repo_initrd, \
                   pxe_comment, \
                   unix_time, \
                   random_str, \
                   inst_flag) values (?, ?, ?, ?, ?, ?, ?, ?)', \
                  [items['pxe_title'], \
                   items['repo_url'], \
                   items['repo_kernel'], \
                   items['repo_initrd'], \
                   items['pxe_comment'], \
                   items['unix_time'], \
                   items['random_str'], \
                   items['inst_flag']\
                   ])
    except sqlite3.Error as e:
        #Remove downloaded files here
        for i in (postfix_kernelfn, postfix_initrdfn):
            os.remove(general_opts['loader_path'] + id_random + i)
        return render_template('failed.html', failed_msg = "Database error: " + str(e))
    g.db.commit()

    # Fetch first 10 entires from the database

    cur = g.db.execute('SELECT pxe_title,\
                            repo_url,\
                            repo_kernel,\
                            repo_initrd,\
                            inst_flag FROM pxeitems order by id desc')
    pxe_entries = [ dict(pxe_title=row[0], \
                    repo_url=row[1], \
                    repo_kernel=row[2], \
                    repo_initrd=row[3], \
                    inst_flag=row[4]) for row in cur.fetchall()[:10]\
                   ]

    # Write the entries to PXE configure file

    try:
        fpxe = open(general_opts['pxe_file'],'w')
    except IOError as e:
        for i in ("0","1"):
            os.remove(general_opts['loader_path'] + id_random + "-" + i)
        g.db.execute('DELETE FROM pxeitems WHERE id = (SELECT max(id) FROM pxeitems)')
        return render_template('failed.html', failed_msg = e)

    for i in pxefile_opts['pxe_header']:
        fpxe.write(i + '\n')

    pxe_index = 'a'
    for pxe_entry in pxe_entries:
        fpxe.write('label {0}\n  menu label ^{0} - {1}\n  menu indent 2\n  kernel {2}\n  append initrd=loader{3} {4} install={5}\n\n'.format(\
                pxe_index,\
                pxe_entry['pxe_title'],\
                general_opts['loader_path'] + items['unix_time'] + items['random_str'] + postfix_kernelfn, \
                general_opts['loader_path'] + items['unix_time'] + items['random_str'] + postfix_initrdfn, \
                boot_opts_gen(pxe_entry['inst_flag']),items['repo_url']))
        pxe_index = chr(ord(pxe_index)+1)

    for i in pxefile_opts['pxe_footer']:
        fpxe.write(i + '\n')
    fpxe.close

    # Remove the out of service kernel files
    # Fetch the 11th entries, get the file name
    cur = g.db.execute('SELECT unix_time, random_str\
                            FROM pxeitems order by id desc LIMIT 1 OFFSET 10')

    try:
        id_random_toberm=''.join(cur.fetchone())
    except:
        #If can not fetch (only less then 10 items), then pass
        pass

    for i in [postfix_kernelfn, postfix_initrdfn]:
        try:
            os.remove(general_opts['loader_path'] + id_random_toberm + i)
        except:
            #If the file not exist, then pass
            pass

    flash(u'New entry was successfully posted','green')
    return redirect(url_for('form'))

if __name__ == '__main__':
    if len(sys.argv) == 2:
        if sys.argv[1] == '--initdb':
            init_db()
        elif sys.argv[1] == 'server':

            if not os.path.isfile(general_opts['database']): 
                print("Database is not available!\nCreate with --initdb")
                sys.exit()
            if not os.path.isfile(general_opts['pxe_file']): 
                print("PXE file is not available!\nPlease check the configuration")
                sys.exit()

#            app.debug = True
            app.run(host='0.0.0.0')
        else:
            prt_help()
    else:
        prt_help()
