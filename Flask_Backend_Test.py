from flask import Flask,request, render_template, redirect, url_for, session, flash, send_file, Response
from azure.storage.blob import BlobServiceClient
import sqlite3
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
import os
from pandas import DataFrame
import pandas
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from dotenv import load_dotenv
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2.rfc6749 import errors
from io import BytesIO
from Password_Creation_Simple_Test import create_password
from sqlalchemy import create_engine, text
import openpyxl
from sqlalchemy.exc import OperationalError
import datetime
from datetime import date, timedelta
# import win32com.client as client
import zipfile




load_dotenv()

engine = create_engine(os.getenv("DATABASE_URL"), pool_size=10, max_overflow=20, echo=True)
app = Flask(__name__, template_folder=r'templates', static_folder=r'static')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
EIDOS_SECRET_KEY = os.getenv('EIDOS_SECRET')

# UPLOAD_FOLDER = r"Z:\Test Files"
# UPLOAD_WORKFOLDER =  r"T:\Accounts Payable\AP WORKING FOLDER\AP Invoices\11 MAY 2025\05-06-2025\Chris\Test Network"
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = None
users ={}
admins = {
    "ADMIN": {"password": "chris123"}
}
personal = ["isodreezy@aim.com"]



class User(UserMixin):
    def __init__(self, username, name = None):
        self.id = username
        self.name = name

def get_reduri(request_val):
    print(request_val.host_url)

    if request_val.host_url == "https://eidos-tests.ngrok.app/":
        red_uri_str = "NGROK_REDIRECT_URI"
        print("Using NGROK.")
        return red_uri_str
    elif request_val.host_url == "http://localhost/" or request_val.host_url == "https://localhost:80":
        red_uri_str = "LOCAL_REDIRECT_URI"
        print("Using Local.")
        return red_uri_str
    elif request_val.host_url == "https://journey2eidos.com/":
        red_uri_str = "REND_REDIRECT_URI"
        print("Using Render.")
        return red_uri_str
    else:
        print(f"{request_val.host_url} is the base url.")
        flash("The url you're using doesn't match the valid redirect URIs.")
        return redirect('/')

# def excel_table_splitter(excel_file, split_by_column,folder_target, file_name):
#
#     excel_sheet = pandas.read_excel(excel_file)
#     excel_sheet.columns = excel_sheet.columns.str.replace('\n','')
#     print(excel_sheet.columns)
#
#     unique_ind = excel_sheet[split_by_column].unique()
#
#
#     def process_person(person):
#
#
#         individual_df = excel_sheet[excel_sheet[split_by_column] == person]
#         print(individual_df)
#         individual_df.reset_index(drop=True)
#         new_excel_path = fr"{folder_target}\{person} {file_name}.xlsx"
#         individual_df.to_excel(new_excel_path, index=False)
#         generate_statement_email(person,new_excel_path)
#
#     for ind in unique_ind:
#         process_person(ind)


def pandafy(excel_doc, card_type, voucher_id, ije_id, exclude_mgl=False,exclude_mr=False):
    try:
        df = pandas.read_excel(excel_doc)
        print("Reading csv.")
    except ValueError:
        df = pandas.read_csv(excel_doc)
    review_df = pandas.DataFrame()
    try:
        coar_csv_df = pandas.read_csv(r"CHARTOFACCTS.csv")
    except FileNotFoundError:
        coar_csv_df = pandas.DataFrame({'GL Account': ['0-0-0000-0000']})
    posting_date = "06/21/1996"
    period=""
    if card_type == 'CHASE':
        print(df.keys())
        chase_df_keys = list(df.keys())
        valid_gl_cols = chase_df_keys[chase_df_keys.index('Notes')+1:chase_df_keys.index('User Department')]
        df["Name"] = df["First Name"] + " " + df["Last Name"]
        # df["Final Gl"] = df[valid_gl_cols].bfill(axis=1).iloc[:, 0]
        gl_items = df[valid_gl_cols].apply(lambda row: row.dropna().tolist(), axis=1)

        df["Final Gl"] = ["NOT SELECTED" if not x else str(x[0]).split(' ')[0] for x in gl_items]
        df["Final ProjID"] = ["" if not x else proj_id_helper(x) for x in gl_items]

        df["Amount"] = (
            df["Amount"]
            .astype(str).str.replace("$", "", regex=False)
            .astype(str).str.replace(",", "", regex=False)
            .astype(str).str.replace("(", "-", regex=False)
            .astype(str).str.replace(")", "", regex=False)
        )
        print(df)
        df["Amount"] = pandas.to_numeric(df["Amount"])
        print(df["Amount"])
        df["Debit"] = [abs(x) if x<0 else "" for x in df["Amount"]]
        df["Credit"] = [x if x>0 else "" for x in df["Amount"]]
        df["Gl Check"] = ["True" if x in coar_csv_df['GL Account'].to_list() else "False" for x in df["Final Gl"]]
        posting_date = str((
                pandas.to_datetime(df["Authorized At (UTC)"])[0]
                + pandas.offsets.MonthEnd(0)).strftime("%m/%d/%Y"))

        print(posting_date)
        period = datetime.datetime.strptime(posting_date,"%m/%d/%Y").strftime("%B %Y")
        # df["Date"] = df['Authorized At (UTC)'].astype(str).str.split(" ")[0]
        # print(df["Final Gl"])
        df['Date'] = pandas.to_datetime(df["Authorized At (UTC)"]).dt.strftime("%m/%d/%Y")
        review_df = df[['Name', 'Merchant','Debit','Credit', 'Receipt?', 'Date', 'Final Gl', 'Final ProjID','Gl Check', 'Notes']].copy()
        if exclude_mgl and not exclude_mr:
            review_df = review_df.loc[review_df['Final Gl'] != "nan"]
        elif exclude_mr and not exclude_mgl:
            review_df = review_df.loc[review_df['Receipt?'] == "Y"]
        elif exclude_mr and exclude_mgl:
            review_df = review_df.loc[review_df['Final Gl'] != "nan"]
            review_df = review_df.loc[review_df['Receipt?'] == "Y"]

        df["Debit"] = pandas.to_numeric(df["Debit"], errors="coerce")
        df["Credit"] = pandas.to_numeric(df["Credit"], errors="coerce")
        total = (df["Debit"].sum() - df["Credit"].sum()).round(2)
        print("Total is:", total)
        review_df.loc[len(review_df)] = ['Payment', period,'',total,"N/A", posting_date, '1-0-4378-5600', '', 'TRUE','Our JPM payment']

        # Let's try just returning a "proper" dataframe html table.
        # review_df.to_csv(os.path.join(completed_directory,f"{period} {card_type} Review Excel.csv"), index=False)
    print(review_df)
    return review_df, card_type, period, voucher_id, ije_id
    # Each review df should have the sam format.

def make_je_files(target_df, completed_directory=r"T:\Accounts Payable\AP WORKING FOLDER\AP Invoices\11 May 2026\Chris\Credit Card Auto Attempt"):
    review_df, card_type, period, voucher_id, ije_id = target_df
    posting_date = review_df['Date'].to_list()[-1]
    month_of_charge = posting_date.split("/")[0]
    print(f"Month of charge: {month_of_charge}")
    date_value = posting_date.replace("/", "")[:4] + posting_date[-2:]
    size_of_review = len(review_df)

    je_list = ["JE" for _ in range(size_of_review)]
    gl_list_column = ["NEED GL" if x=="nan" else x.replace("-","") for x in review_df["Final Gl"]]
    prj_id_column = ["" if not x else x for x in review_df["Final ProjID"]]
    debit_amounts_column = ["" if not x else int(round((x*100))) for x in review_df["Debit"]]
    credit_amounts_column = ["" if not x else int(round((x*100))) for x in review_df["Credit"]]
    description_column = [month_of_charge+card_type+"-"+voucher_id+"-"+x for x in review_df['Merchant'].to_list()]
    ije_id_column = [ije_id for _ in range(size_of_review)]
    date_column = [str(date_value) for _ in range(size_of_review)]

    print(len(je_list))
    print(len(gl_list_column))
    print(len(prj_id_column))
    print(len(debit_amounts_column))
    print(len(credit_amounts_column))
    print(len(description_column))
    print(len(ije_id_column))
    print(len(date_column))

    rcc_excel_file_name = f"{period} {card_type} Review Excel.csv"
    r_card_output = BytesIO()

    # After the html is corrected, it converts back to a dataframe with the new values and comes here for file creation.

    review_df.to_csv(r_card_output, index=False)
    r_card_output.seek(0)
    review_excel = r_card_output.read()
    upload_dataframe = pandas.DataFrame({'JE Column':je_list, 'GL Column':gl_list_column,
                                     'Debits':debit_amounts_column, 'Credits':credit_amounts_column,
                                     'Description':description_column, 'IJE ID':ije_id_column, 'Post Date':date_column, 'Empty1':'','Empty2':'', 'ProjID':prj_id_column, })
    cc_excel_file_name = f"{period} {card_type} Final.xlsx"
    f_card_output = BytesIO()
    with pandas.ExcelWriter(f_card_output, engine='xlsxwriter') as writer:
        upload_dataframe.to_excel(writer,sheet_name='Upload File',header=False, index=False)
        worksheet = writer.sheets['Upload File']
        worksheet.set_column('A:A', 2)
        worksheet.set_column('B:B', 10)
        worksheet.set_column('C:C', 13)
        worksheet.set_column('D:D', 13)
        worksheet.set_column('E:E', 30)
        worksheet.set_column('F:F', 10)
        worksheet.set_column('G:G', 8)
        worksheet.set_column('H:H', 7)
        worksheet.set_column('I:I', 5)
        worksheet.set_column('J:J', 15)
        print("Closing Final excel")

    f_card_output.seek(0)
    final_excel = f_card_output.read()
    ije_package = BytesIO()
    with zipfile.ZipFile(ije_package, mode='w',compression=zipfile.ZIP_STORED) as z:
        z.writestr(cc_excel_file_name,final_excel)
        z.writestr(rcc_excel_file_name,review_excel)
    ije_package.seek(0)
    # ije_zip = ije_package.read(0)
    return ije_package
    # print(upload_dataframe)

# def generate_statement_email(person_name, excel_attachment):
#     seven_days_from_today = date.today() + timedelta(days=7)
#
#     outlook = client.Dispatch('Outlook.Application')
#     message = outlook.CreateItem(0)
#     # message.Display()
#
#     statement_type = "STATEMENT TYPE"
#     message.To = "Place Holder"
#     message.CC = "accounts.payable@brooklaw.edu"
#     message.Subject = f"{person_name} {statement_type}"
#     lost_or_missing_file = r"documents/Lost or Missing Receipt Form.docx"
#     message.Attachments.Add(lost_or_missing_file)
#     message.Attachments.Add(excel_attachment)
#
#     message_test = f"""
#     Hi {person_name}, <br>
#     <br>
#     Please review your {statement_type} activity and update the coding in column I of the excel sheet.
#     After updating, save the Excel file as "Approved" and forward this email back to me with the updated excel file and the receipts to validate the purchases.
#     If a receipt is missing, please complete the attached form.<br>
#     <br>
#     Should you have any questions, please don't hesitate to ask.<br>
#     <br>
#     Please complete it by {seven_days_from_today.strftime("%B %d, %Y")}.
#     """
#
#     image_path = r"documents\bls_img.png"
#     attachment = message.Attachments.Add(image_path)
#     # Remember it was working with http, I just changed to https without testing because
#     # the warning was annoying me.
#     attachment.PropertyAccessor.SetProperty(
#         "https://schemas.microsoft.com/mapi/proptag/0x3712001F",
#         "logo_cid"
#     )
#
#     message.HTMLbody = f"""<!DOCTYPE html>
#
#     <p>{message_test}</p>
#
#     <p>
#
#
#
#         <br>
#         <br>
#         <span style='font-size:10.0pt;font-family:"Times New Roman",serif'>Best Regards,</span> <br>
#         <br>
#         <span> <b style='font-size:10.0pt;font-family:"Times New Roman",serif'>Erina Pae </b> </span> <br>
#
#         <span style='font-size:10.0pt;font-family:"Times New Roman",serif'>Accounts Payable & Procurement Manager </span> <br>
#
#         <span style='font-size:10.0pt;font-family:"Times New Roman",serif'>Brooklyn Law School </span> <br>
#
#         <span style='font-size:10.0pt;font-family:"Times New Roman",serif'>(718)-780-0305 </span> <br>
#
#         <span style='font-size:10.0pt;font-family:"Times New Roman",serif'><a href="mailto:accounts.payable@brooklaw.edu">accounts.payable@brooklaw.edu</a></span> <br>
#         <img src="cid:logo_cid" width="190">
#     </p>"""
#
#     message.Save()


def proj_id_helper(gl_info_list):
    try:
        if len(gl_info_list[1]) > 15:
            prj_id = None
        else:
            prj_id = gl_info_list[1]
    except IndexError:
        prj_id = None
    return prj_id


@app.after_request
def add_security_headers(response):
    response.headers['Strict-Transport-Security'] = 'max-age=63072000; includeSubDomains'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Content-Security-Policy'] = ("default-src 'self' https:; "
                                                   "font-src 'self' https: data:; "
                                                   "img-src 'self' https: data:; "
                                                   "script-src 'self' https:; "
                                                   "style-src 'self' https: 'unsafe-inline';"
                                                   "frame-src 'self' "
                                                       "blob: "
                                                       "https://informer5.brooklaw.edu "
                                                       "https://*.journey2eidos.com "
                                                       "https://*.eidos-tests.ngrok.app "
                                                       "http://*.localhost;")
    response.headers['Referrer-Policy'] = 'same-origin'
    return response

@login_manager.user_loader
def load_user(user_id):
    if user_id in users:

        return User(user_id)
    elif user_id in admins:
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
        # print(users[username]['password'], password)
        if (username in admins and admins[username]['password']  == password) or (username in personal) or (username.endswith("@brooklaw.edu") and users[username]['password'] == EIDOS_SECRET_KEY):
            print("Successfully passed login check.")
            user = User(username)
            if username in admins:
                session['user_name'] = "ADMIN"
            login_user(user)
            print("Successfully logged in.")
            return redirect('/')
        else:
            print("Invalid username or password.")
            session.clear()
            session.pop('_flashes', None)
            flash("Invalid username or password.")
            return redirect(url_for('login'))

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
    print("Attempting to reach microsoft.")
    red_uri = get_reduri(request)
    if isinstance(red_uri, Response):
        return red_uri
    oauth = OAuth2Session(
        os.getenv("CLIENT_ID"),
        scope=OAUTH_SCOPE,
        redirect_uri=os.getenv(red_uri)
    )
    auth_url, state = oauth.authorization_url(AUTH_BASE_URL, prompt = 'select_account')
    session['oauth_state'] = state
    print("Successfully reached Microsoft SSO.")
    return redirect(auth_url)

@app.route('/auth/ms-callback')
def auth_callback():
    print("Authorizing user...")

    red_uri = get_reduri(request)
    if isinstance(red_uri, Response):
        return red_uri
    oauth = OAuth2Session(
        os.getenv("CLIENT_ID"),
        redirect_uri=os.getenv(red_uri),
        state=session.get('oauth_state')
    )
    print("Microsoft user authorized.")

    print(oauth.state)

    # Its annoying that its gray, but the value
    try:
        oauth.fetch_token(
        TOKEN_URL,
        client_secret=os.getenv("CLIENT_SECRET"),
        authorization_response=request.url
    )
        # session.pop('oauth_state', None)
    except errors.AccessDeniedError:
        print("Access denied, please make sure your admin/IT allows this app access.")
        session.clear()
        session.pop('_flashes', None)
        flash("Please check with admin/IT to add permissions for this site!")
        return redirect('/')

    user_info = oauth.get(USER_INFO_URL).json()
    email = user_info.get("mail") or user_info.get("userPrincipalName")
    email = email.lower().strip()
    if not email:
        return "Unable to retrieve email address.", 400

    if email not in users:
        users[email] = {'password': None}

    if not email.endswith("@brooklaw.edu") and email not in admins.keys() and email not in personal:
    # if not email == "christopher.dessourc@brooklaw.edu":

        session.clear()
        session.pop('_flashes', None)
        flash("Only Brooklaw emails. Sorry!")
        return redirect('/')

    else:
        print("Valid user:", email)
        if email == 'admin':
            full_name = "ADMINISTRATOR"
        else:
            full_name = user_info.get("displayName")
        if email.endswith("@brooklaw.edu"):
            users[email]['password']=EIDOS_SECRET_KEY

        user = User(email, full_name)
        session['user_name'] = full_name

        login_user(user)

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
@app.route('/accruals-prepaid')
@login_required
def serve_form():
    print("Serving accruals-prepaid page.")
    return render_template('ap_upload_test.html', user_name=session.get('user_name'))

@app.route('/')
@login_required
def serve_main():
    user = current_user
    if not user:
        return redirect('/login')  # or some response
    return redirect('/accruals-prepaid')

# @app.route('/favicon.ico')
# def favicon():
#     return send_from_directory(os.path.join(app.root_path, 'static'),
#                           'favicon.ico',mimetype='image/vnd.microsoft.icon')

@app.route('/other-projects')
@login_required
def other_projects():
    return render_template('ProjectsPage.html')

qualified_users = ["Christopher Dessources", "Jeffrey Dulow", "admin"]

@app.route("/credit-card-prep")
@login_required
def credit_card_prep():
    return render_template('credit_card_prepper.html')

@app.route("/split", methods=["POST"])
@login_required
def split():
    excel_targ = request.files.get("ExcelFile")
    print(excel_targ)
    split_col = request.form.get("SplitBy")
    folder_targ = request.form.get("TargetFolder")
    file_name_targ = request.form.get("NewFileName")
    # Make a variable that gets a choice element like dropdown and do an if. if card prep for td and amex, table splitter.
    # if chase oand other card ije generation,pandafy.

    # excel_table_splitter(excel_file=excel_targ, split_by_column=split_col, folder_target=folder_targ, file_name=file_name_targ)
    print("Sorry temporarily down....Render is Linux only.")
    return redirect('/credit-card-prep')

@app.route("/card_convert", methods=["POST"])
@login_required
def card_data_conversion():
    excel_targ = request.files.get("ExcelFileConvert")
    print(excel_targ)
    card_type = request.form.get("cardType")
    card_payment_voucher = request.form.get("cardVoucherNumber")
    ije_number = request.form.get("ijeNumber")
    ije_zip_bytes = make_je_files(pandafy(
            excel_targ,
            voucher_id=card_payment_voucher, ije_id=ije_number, card_type=card_type, exclude_mgl=False,
            exclude_mr=False))
    return send_file(
        ije_zip_bytes,
        as_attachment=True,
        download_name='IJE_FILES_PACKAGE.zip'
    )

@app.route('/remote-api', methods=['POST', 'GET'])
def remote_api():
    print(request.json)
    return {'status': 'OK'}

@app.route('/download-submissions')
@login_required
def download_excel():
    try:
        if session["user_name"] in admins or session["user_name"] in personal:
            print(admins,personal)
            print(f"Attempting to download total excel from DB for {session['user_name']}.")
            df = pandas.read_sql('SELECT * FROM accruals', con=engine)
            print("Successfully downloaded total excel from DB.")

        else:
            print(f"Attempting to download excel from DB for {session['user_name']}.")
            df = pandas.read_sql('SELECT * FROM accruals WHERE "Submitter" = %(user)s', con=engine,
                                 params={"user": session["user_name"]})
            print("Successfully downloaded excel from DB.")

        output = BytesIO()
        with pandas.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Accruals')

        output.seek(0)
        print("File downloaded.")
        return send_file(
            output,
            as_attachment=True,
            download_name='accruals_export.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except OperationalError as e:
        print(f"Houston we have a database error. Its likely that the network blocks anything inbound from port 5432.")
        flash("Database is not connected. Please try again later.", "info")
        return redirect('/accruals-prepaid')


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



        prepaid_fys = request.form.getlist('Fiscal Year')
        prepai_period = request.form.getlist('prepaidPeriod')
        prepaid_dmy = request.form.getlist('Days/Months/Years')

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

        print(f"Prepaid Fiscal Year: {prepaid_fys}. Period: {prepai_period}. Days/Months/Years: {prepaid_dmy}.")
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

            accrual_entry_df['Prepaid Year'] = prepaid_fys
            accrual_entry_df['Prepaid Period'] = prepai_period
            accrual_entry_df['Days/Months/Years'] = prepaid_dmy

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
            except Exception:
                print("Failed to connect to Azure blob service")
                pass


            # print(f"Vendor:{vendor} "  f"Invoice Date: {invoice_dt} " f"Amount: {amount} " f"GL Code List: {gl_codes} "
            # f"Department: {department} " f"Fixed Asset Check:{fa_check} " f"Estimate Check: {est_check} " f"Gl Code
            # Amount List: {gl_code_amounts} " f"Gl Code Amount List: {project_ids}")
            flash("Successfully submitted.")
            result.close()
            return redirect(url_for('serve_form'))
            # return f"Success! File saved to: {save_path1} and {save_path2} with accrual id: {main_accrual_tag}."

        return "Fail, check the name again. No file received"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 80))
    app.run(host='0.0.0.0', port=port)

    # Incoming IP: ['']
    # Date

#command prompt is: ngrok http --url=eidos-tests.ngrok.app 80 --basic-auth="bls:bls11201"
#You need to go via http://localhost:5000/main since i use local host as the redirect url.
# inventory number vendor name gl code submitter
# if fixed asset, must start with a 4 and must have project code, 13 digit long
