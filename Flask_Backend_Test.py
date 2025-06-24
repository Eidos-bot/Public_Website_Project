from flask import Flask,request, render_template, redirect, url_for, session, flash
from azure.storage.blob import BlobServiceClient
import sqlite3
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
import os
from pandas import DataFrame
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from dotenv import load_dotenv
from requests_oauthlib import OAuth2Session

from Password_Creation_Simple_Test import create_password
from sqlalchemy import create_engine, text

DATABASE_URL = (
    "postgresql://eidos:L0SrVaedulB9tnFzkUoc2twhIbWVAGz9@"
    "dpg-d1d0idfdiees73cbhvh0-a.ohio-postgres.render.com:5432/accrual_db"
    "?sslmode=require"
)

engine = create_engine(DATABASE_URL, echo=True)

load_dotenv()
app = Flask(__name__, template_folder=r'templates', static_folder=r'static')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# UPLOAD_FOLDER = r"Z:\Test Files"
# UPLOAD_WORKFOLDER =  r"T:\Accounts Payable\AP WORKING FOLDER\AP Invoices\11 MAY 2025\05-06-2025\Chris\Test Network"
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

users = {
    "ChrisAdmin": {"password": "temppass"},
}


class User(UserMixin):
    def __init__(self, username, name = None):
        self.id = username
        self.name = name

@login_manager.user_loader
def load_user(user_id):
    if user_id in users:

        return User(user_id)

    return None

@app.route('/account_creation', methods=['GET', 'POST'])
def serve_ac_form():
    return render_template('account_creation_page.html')


@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username in users and users[username]['password']  == password and username.endswith("@brooklaw.edu"):

            user = User(username)

            login_user(user)
            return redirect(url_for('serve_form'))
        return "Invalid credentials", 401
    return render_template('Homescreen.html')
# ip_filter = IPFilter(app, ruleset=Whitelist())
# ip_filter.ruleset.permit()


#Was my attempt to see ips so i could whitelist. Pointless with basic auth
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)

UPLOAD_FOLDER = r"\\ChrisD-Main\Test Network\Test Files"
UPLOAD_WORKFOLDER =r"\\finance\Treasurer\Accounts Payable\AP WORKING FOLDER\AP Invoices\11 MAY 2025\05-06-2025\Chris\finance Test Network"
local_folder = r"C:\Test Network\Test Files"

AUTH_BASE_URL = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
TOKEN_URL = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'
USER_INFO_URL = 'https://graph.microsoft.com/v1.0/me'
OAUTH_SCOPE = ['User.Read']

@app.route('/login/microsoft')
def login_microsoft():
    oauth = OAuth2Session(
        os.getenv("CLIENT_ID"),
        scope=OAUTH_SCOPE,
        redirect_uri=os.getenv("REDIRECT_URI")
    )
    auth_url, state = oauth.authorization_url(AUTH_BASE_URL, prompt = 'select_account')
    session['oauth_state'] = state
    return redirect(auth_url)

@app.route('/auth/callback')
def auth_callback():
    oauth = OAuth2Session(
        os.getenv("CLIENT_ID"),
        redirect_uri=os.getenv("REDIRECT_URI"),
        state=session.get('oauth_state')
    )
    print(oauth.state)

    # Its annoying that its gray, but the value
    oauth.fetch_token(
        TOKEN_URL,
        client_secret=os.getenv("CLIENT_SECRET"),
        authorization_response=request.url
    )

    user_info = oauth.get(USER_INFO_URL).json()
    email = user_info.get("mail") or user_info.get("userPrincipalName")

    if not email:
        return "Unable to retrieve email address.", 400

    if email not in users:
        users[email] = {'password': None}
    if not email.endswith("@brooklaw.edu"):
        flash("You must login with a brooklaw.edu email address.")
        return redirect('/login')
    full_name = user_info.get("displayName")
    user = User(email, full_name)
    session['user_name'] = full_name
    login_user(user)
    print(email)
    return redirect(url_for('serve_form'))

@app.route('/logout')
def logout():
    logout_user()
    session.clear()
    # microsoft_logout_url = (
    #         "https://login.microsoftonline.com/common/oauth2/v2.0/logout"
    #         "?post_logout_redirect_uri=" + url_for('login', _external=True)
    # )
    #
    # return redirect(microsoft_logout_url)
    return redirect('/login')

allowed_extensions= {'pdf'}

def gl_transmuter(raw_gl):
    formatted = f"{raw_gl[0]}-{raw_gl[1]}-{raw_gl[2:6]}-{raw_gl[6:]}"
    return formatted

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

# @app.before_request
# def log_ip():
#     forwarded_for = request.headers.get('X-Forwarded-For', request.remote_addr)
#     real_ip = forwarded_for.split(',')
#     print(real_ip)
#     if request.remote_addr != "any ip":
#         abort(404)


# @app.route('/')
# def serve_home():
#     return render_template('sign_in.html')
@app.route('/main')
@login_required
def serve_form():
    return render_template('ap_upload_test.html', user_name=session.get('user_name'))

@app.route('/')
@login_required
def serve_main():

    return

# @app.route('/favicon.ico')
# def favicon():
#     return send_from_directory(os.path.join(app.root_path, 'static'),
#                           'favicon.ico',mimetype='image/vnd.microsoft.icon')

# make sure to have '/upload' in the action link. Without it, you get a 405 error from post requests.
@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    with engine.connect() as result:

        conn = result.execute(text('SELECT MAX("Accrual Tag") FROM accruals'))

        max_tag = conn.scalar()

        if max_tag is None:
           accrual_tag2 = 1
        else:
            current_num = int(max_tag.replace("ACC", ""))
            accrual_tag2 = current_num + 1
        accrual_tag1 = "ACC"

        accrual_tag3 = "{:05d}".format(accrual_tag2)
        main_accrual_tag = accrual_tag1 + accrual_tag3
        uploaded_file = request.files.get('file')
        print(current_user.id)

        raw_gl_codes = request.form.getlist('GL')
        gl_codes = [gl_transmuter(x) for x in raw_gl_codes]
        gl_code_amounts = request.form.getlist('Amount')
        project_ids = request.form.getlist('Project ID')
        liabilities = ["4-6-0605-2000" if x.startswith("4") else "1-6-0610-2000" for x in gl_codes]

        vendor = request.form.get('Vendor')
        invoice_dt = request.form.get('Invoice Date')
        amount = request.form.get('Gl Amount Total')
        department = request.form.get('Department')
        description = request.form.get('Description')
        invoice_num = request.form.get('Invoice Number')
        est_check = "Estimate" if request.form.get('Estimate Check') == "on" else "Actual"
        fa_check = "Fixed Asset" if request.form.get('Asset Check') == "on" else "Not Asset"
        fa_check_log = request.form.get('Asset Check')
        est_check_log = request.form.get('Estimate Check')

        print(f"Fixed asset: {fa_check_log}. Estimate: {est_check_log}")
        submitter = request.form.get('Submitter')


            # uploaded_file.save(os.path.join(UPLOAD_FOLDER, uploaded_file.filename))
        if uploaded_file and uploaded_file.filename and allowed_file(uploaded_file.filename):

            accrual_entry_df = DataFrame({'Budget Codes': gl_codes,
                                          'Liabilities' : liabilities,
                                   'Budget Code Amounts': gl_code_amounts,
                                   'Project IDs': project_ids})

            accrual_entry_df['Vendor'] = vendor
            accrual_entry_df['Description'] = description
            accrual_entry_df['Invoice Date'] = invoice_dt
            accrual_entry_df['Invoice Number'] = invoice_num
            accrual_entry_df['Estimate'] = est_check
            accrual_entry_df['Fixed Asset'] = fa_check
            accrual_entry_df['Total Amount'] = amount
            accrual_entry_df['Submitter'] = submitter
            accrual_entry_df['Department'] = department
            accrual_entry_df['Accrual Tag'] = main_accrual_tag


            filename = secure_filename(uploaded_file.filename)
            save_path1 = os.path.join(UPLOAD_FOLDER, filename)
            save_path2 = os.path.join(UPLOAD_WORKFOLDER, filename)

            print(accrual_entry_df)
            # accrual_entry_df.to_csv(save_path1)
            # This is where further action on the files would take place. Y

            ##uploaded_file.save(save_path1)
            # You need to seek again if saving to multiple locations. After first save, data will be zero for subsequent ones.
            ##uploaded_file.seek(0)
            # Seek everytime you 'touch' the binary data. Using read as a check wasn't helping because it did the reset
            # after the save.
            try:
                ##uploaded_file.save(save_path2)
                # accrual_entry_df.to_csv(f"{UPLOAD_WORKFOLDER}\\accrual_entry_df.csv",mode='a', header=False, index=False)
                # accrual_entry_df.to_csv(f"{local_folder}\\accrual_entry_df.csv",mode='a', header=True, index=False)
                accrual_entry_df.to_sql("accruals", con=engine, if_exists="append", index=False)
                accrual_tag2+=1
            except FileNotFoundError:
                return "Server is probably disconnected from the finance drive. Please let christopher.dessourc@brooklaw.edu know."

            azure_connection_string = os.getenv("AZURE_CONNECTION_STRING")
            azure_container = "accrualblobcontainer"
            try:
                blob_service_client = BlobServiceClient.from_connection_string(azure_connection_string)
                container_client = blob_service_client.get_container_client(azure_container)
                blob_name = f"{main_accrual_tag}_{secure_filename(uploaded_file.filename)}"
                blob_client = container_client.get_blob_client(blob_name)
                uploaded_file.stream.seek(0)
                blob_client.upload_blob(uploaded_file.stream, overwrite=True)
            except Exception as e:
                print(e)
                pass


            # print(f"Vendor:{vendor} "  f"Invoice Date: {invoice_dt} " f"Amount: {amount} " f"GL Code List: {gl_codes} "
            # f"Department: {department} " f"Fixed Asset Check:{fa_check} " f"Estimate Check: {est_check} " f"Gl Code
            # Amount List: {gl_code_amounts} " f"Gl Code Amount List: {project_ids}")
            flash("Successfully submitted.")
            return redirect(url_for('serve_form'))
            # return f"Success! File saved to: {save_path1} and {save_path2} with accrual id: {main_accrual_tag}."

        return "Fail, check the name again. No file received"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

    # Incoming IP: ['']
    # Date

#command prompt is: ngrok http --url=eidos-tests.ngrok.app 80 --basic-auth="bls:bls11201"
# inventory number vendor name gl code submitter
# if fixed asset, must start with a 4 and must have project code, 13 digit long
