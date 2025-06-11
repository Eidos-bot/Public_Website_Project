from flask import Flask,request, render_template
import sqlite3
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
import os
from pandas import DataFrame

app = Flask(__name__, template_folder=r'templates', static_folder=r'static')
#Was my attempt to see ips so i could whitelist. Pointless with basic auth
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)
# UPLOAD_FOLDER = r"Z:\Test Files"
# UPLOAD_WORKFOLDER =  r"T:\Accounts Payable\AP WORKING FOLDER\AP Invoices\11 MAY 2025\05-06-2025\Chris\Test Network"

# ip_filter = IPFilter(app, ruleset=Whitelist())
# ip_filter.ruleset.permit(["2600:4808:3954:c901::/64","24.47.4.0/24"])



UPLOAD_FOLDER = r"\\ChrisD-Main\Test Network\Test Files"
UPLOAD_WORKFOLDER =r"\\finance\Treasurer\Accounts Payable\AP WORKING FOLDER\AP Invoices\11 MAY 2025\05-06-2025\Chris\finance Test Network"
local_folder = r"C:\Test Network\Test Files"


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


@app.route('/')
def serve_form():
    return render_template('ap_upload_test.html')

# @app.route('/favicon.ico')
# def favicon():
#     return send_from_directory(os.path.join(app.root_path, 'static'),
#                           'favicon.ico',mimetype='image/vnd.microsoft.icon')

# make sure to have '/upload' in the action link. Without it, you get a 405 error from post requests.
@app.route('/upload', methods=['POST'])

def upload_file():
    ap_upload_test_database_connection = sqlite3.connect('identifier.sqlite')
    cursor = ap_upload_test_database_connection.cursor()
    cursor.execute('SELECT MAX("Accrual Tag") FROM ACCRUALS')

    max_tag = cursor.fetchone()[0]

    if max_tag is None:
       accrual_tag2 = 1
    else:
        current_num = int(max_tag.replace("ACC", ""))
        accrual_tag2 = current_num + 1
    accrual_tag1 = "ACC"

    accrual_tag3 = "{:05d}".format(accrual_tag2)
    main_accrual_tag = accrual_tag1 + accrual_tag3
    uploaded_file = request.files.get('file')

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
            accrual_entry_df.to_sql("ACCRUALS", ap_upload_test_database_connection, if_exists="append", index=False)
            accrual_tag2+=1
        except FileNotFoundError:
            return "Server is probably disconnected from the finance drive. Please let christopher.dessourc@brooklaw.edu know."



        # print(f"Vendor:{vendor} "  f"Invoice Date: {invoice_dt} " f"Amount: {amount} " f"GL Code List: {gl_codes} "
        # f"Department: {department} " f"Fixed Asset Check:{fa_check} " f"Estimate Check: {est_check} " f"Gl Code
        # Amount List: {gl_code_amounts} " f"Gl Code Amount List: {project_ids}")

        return f"Success! File saved to: {save_path1} and {save_path2}"

    return "Fail, check the name again. No file received"

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=80)

    # Incoming IP: ['']
    # Date

#command prompt is: ngrok http --url=eidos-tests.ngrok.app 80 --basic-auth="bls:bls11201"
# inventory number vendor name gl code submitter
# if fixed asset, must start with a 4 and must have project code, 13 digit long
