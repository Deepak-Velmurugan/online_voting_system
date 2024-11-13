from flask import Flask, render_template, redirect, request, url_for, session, flash
from flask_mysqldb import MySQL
from config import Config
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from flask import send_from_directory



app = Flask(__name__)
app.config.from_object(Config)

mysql = MySQL(app)


# Ensure the upload folder exists
UPLOAD_FOLDER = 'uploads/candidate_photos'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Set a folder to save uploaded images
UPLOAD_FOLDER = 'uploads/candidate_photos'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Limit file types (optional but recommended for security)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['ALLOWED_EXTENSIONS'] = ALLOWED_EXTENSIONS


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Ensure that database interaction runs within the application context
with app.app_context():
    try:
        cur = mysql.connection.cursor()
        cur.execute("select * from users")  # Simple query to test connection
        cur.close()
        print("Database connection established successfully.")
    except Exception as e:
        print("Error connecting to the database:", e)

@app.route('/')
def home():
    return render_template('base.html')

#register page
@app.route('/register', methods=['GET', 'POST'])
def register(): 
    if request.method == 'POST':
        username = request.form['username']
        contact_no = request.form['contact_no']
        password = request.form['password']  # Ensure hashing here
        user_role = 'voter'
        
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO USERS (username, contact_no, password, user_role, is_admin) VALUES (%s, %s, %s, %s, %s)", 
                    (username, contact_no, password, user_role, False))
        mysql.connection.commit()
        cur.close()
        flash('Registration successful!')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM USERS WHERE username=%s AND password=%s", (username, password))
        user = cur.fetchone()
        cur.close()
        
        if user:
            session['logged_in'] = True
            session['user_id'] = user['users_id']
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            session['user_role'] = user['user_role']  # Add user role to the session
            
            if session['is_admin']:
                return redirect(url_for('admin_dashboard'))
            elif session['user_role'] == 'manager':
                return redirect(url_for('manager_dashboard'))
            else:
                return redirect(url_for('vote'))
        else:
            flash('Invalid login credentials')
    return render_template('login.html')


#logging out
@app.route('/logout')
def logout():
    # Remove user session data to log out the user
    session.pop('logged_in', None)
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('is_admin', None)
    flash('You have been logged out successfully!')
    return redirect(url_for('login'))
#------------------------------------------------------------------

@app.route('/vote', methods=['GET', 'POST'])
def vote():
    if 'logged_in' not in session:
        flash('Please log in to access the voting page.')
        return redirect(url_for('login'))
    
    cur = mysql.connection.cursor()

    # GET request: Show available elections and candidates
    if request.method == 'GET':
        cur.execute("SELECT * FROM ELECTIONS WHERE status = 'Upcoming'")
        elections = cur.fetchall()

        # Get all candidates grouped by election_id
        cur.execute("SELECT * FROM CANDIDATE_DETAILS")
        all_candidates = cur.fetchall()

        cur.close()
        return render_template('vote.html', elections=elections, all_candidates=all_candidates)
    
    # POST request: Handle vote submission
    if request.method == 'POST':
        election_id = request.form['election_id']
        candidate_id = request.form['candidate_id']
        user_id = session['user_id']
        
        # Check if the user has already voted in this election
        cur.execute("SELECT * FROM VOTINGS WHERE election_id = %s AND voters_id = %s", (election_id, user_id))
        existing_vote = cur.fetchone()

        if existing_vote:
            flash('You have already voted in this election.')
        else:
            # Insert the vote into the database
            cur.execute("INSERT INTO VOTINGS (election_id, voters_id, candidate_id, vote_date, vote_time) VALUES (%s, %s, %s, %s, %s)", 
                        (election_id, user_id, candidate_id, datetime.now().date(), datetime.now().time()))
            mysql.connection.commit()
            flash('Your vote has been successfully cast!')

        cur.close()
        return redirect(url_for('vote'))

    
#-----------------------------------------------------------------------------------
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'logged_in' in session and session.get('is_admin'):
        cur = mysql.connection.cursor()
        # Query to get elections data
        cur.execute("SELECT * FROM ELECTIONS")
        elections = cur.fetchall()  # Assuming it returns a list of elections
        cur.close()

        # Pass elections data to the template
        return render_template('admin_dashboard.html', elections=elections)
    flash('You do not have permission to access the admin dashboard.')
    return redirect(url_for('login'))
#------------------------------MANAGE ELECTIONS---------------------------------------------
@app.route('/manage_elections', methods=['GET', 'POST'])
def manage_elections():
    if 'logged_in' in session and session.get('is_admin'):
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM ELECTIONS")
        elections = cur.fetchall()
        cur.close()
        
        return render_template('manage_elections.html', elections=elections)
    
    flash('You do not have permission to access this page.')
    return redirect(url_for('login'))

@app.route('/create_election', methods=['GET', 'POST'])
def create_election():
    if 'logged_in' in session and session.get('is_admin'):
        if request.method == 'POST':
            election_name = request.form['election_name']
            starting_date = datetime.strptime(request.form['starting_date'], '%Y-%m-%d').date()
            ending_date = datetime.strptime(request.form['ending_date'], '%Y-%m-%d').date()
            no_of_candidates = request.form['candidates_tot']

            # Check if the ending date is before the starting date
            if ending_date < starting_date:
                flash('Ending date cannot be before the starting date.')
                return render_template('create_election.html')

            status = 'Upcoming'  # Default status for new elections
            inserted_by = session['user_id']  # Assuming the admin's user_id is stored in session

            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO ELECTIONS (election_topic,no_of_candidates, starting_date, ending_Date, status, inserted_by, inserted_on) VALUES (%s, %s, %s, %s, %s, %s, NOW())",
                        (election_name,no_of_candidates,  starting_date, ending_date, status, inserted_by))
            mysql.connection.commit()
            cur.close()

            flash('Election created successfully!')
            return redirect(url_for('admin_dashboard'))
        
        return render_template('create_election.html')
    
    flash('You do not have permission to access this page.')
    return redirect(url_for('login'))

@app.route('/update_election/<int:election_id>', methods=['GET', 'POST'])
def update_election(election_id):
    if 'logged_in' in session and session.get('is_admin'):
        cur = mysql.connection.cursor()

        # Get the current election details
        cur.execute("SELECT * FROM ELECTIONS WHERE elections_id = %s", (election_id,))
        election = cur.fetchone()

        print(f"Election Data: {election}")

        # Fetch all elections to populate the dropdown
        cur.execute("SELECT elections_id, election_topic FROM ELECTIONS")
        elections = cur.fetchall()

        # Determine the current status based on dates
        current_date = datetime.now().date()
        status = 'Upcoming'  # Default status
        if election['starting_date'] <= current_date <= election['ending_Date']:
            status = 'Ongoing'
        elif current_date > election['ending_Date']:
            status = 'Completed'

        if request.method == 'POST':
            election_name = request.form['election_name']
            starting_date = request.form['starting_date']
            ending_date = request.form['ending_date']
            # Check if the ending date is before the starting date
            if ending_date < starting_date:
                flash('Ending date cannot be before the starting date.')
                return render_template('update_election.html', election=election)

            status = request.form['status']  # Status can still be modified by admin if needed
            inserted_by = session['user_id']  # Assuming the admin's user_id is stored in session
            
            cur.execute("""
                UPDATE ELECTIONS
                SET election_topic = %s, starting_date = %s, ending_Date = %s, status = %s, inserted_by = %s
                WHERE elections_id = %s
            """, (election_name, starting_date, ending_date, status, inserted_by, election_id))
            mysql.connection.commit()
            cur.close()
            flash('Election updated successfully!')
            return redirect(url_for('admin_dashboard'))

        cur.close()
        return render_template('update_election.html', election=election, elections=elections, status=status)

    flash('You do not have permission to access this page.')
    return redirect(url_for('login'))

import MySQLdb

# Assuming you have already initialized `mysql` like this:
# mysql = MySQL(app)

@app.route('/delete_election/<int:election_id>')
def delete_election(election_id):
    if 'logged_in' in session and session.get('is_admin'):
        try:
            cur = mysql.connection.cursor()  # Ensure `mysql` is your initialized MySQL instance

            # Delete only the election record; triggers will handle related deletions
            cur.execute("DELETE FROM ELECTIONS WHERE elections_id = %s", (election_id,))
            mysql.connection.commit()
            cur.close()

            flash('Election and associated records deleted successfully!')
            return redirect(url_for('admin_dashboard'))
        except MySQLdb.IntegrityError as e:  # Use MySQLdb for exception handling
            flash(f"Error: {e}")
            return redirect(url_for('admin_dashboard'))
    flash('You do not have permission to access this page.')
    return redirect(url_for('login'))




@app.route('/view_results/<int:election_id>')
def view_results(election_id):
    if 'logged_in' not in session:
        flash('Please log in to view election results.')
        return redirect(url_for('login'))
    
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT cd.candidate_name, COUNT(v.candidate_id) AS vote_count
        FROM VOTINGS v
        JOIN CANDIDATE_DETAILS cd ON v.candidate_id = cd.candidate_id
        WHERE v.election_id = %s
        GROUP BY cd.candidate_name
        ORDER BY vote_count DESC
    """, (election_id,))
    
    results = cur.fetchall()

    # Fetch the election details to pass to the template
    cur.execute("SELECT * FROM ELECTIONS WHERE elections_id = %s", (election_id,))
    election = cur.fetchone()
    cur.close()
    
    if not election:
        flash('Election not found.')
        return redirect(url_for('home'))
    
    # Pass both results and election data to the template
    return render_template('view_results.html', results=results, election=election)

#-----------------------------------------------------------------------------------
@app.route('/create_manager', methods=['GET', 'POST'])
def create_manager():
    if 'logged_in' in session and session.get('is_admin'):
        if request.method == 'POST':
            username = request.form['username']
            contact_no = request.form['contact_no']
            password = request.form['password']  # Make sure to hash this in production
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO USERS (username, contact_no, password, user_role, is_admin) VALUES (%s, %s, %s, %s, %s)", 
                        (username, contact_no, password, 'manager', False))
            mysql.connection.commit()
            cur.close()
            flash('Manager created successfully!')
            return redirect(url_for('admin_dashboard'))
        return render_template('create_manager.html')
    flash('Access restricted to admins only.')
    return redirect(url_for('login'))

@app.route('/assign_election', methods=['GET', 'POST'])
def assign_election():
    if 'logged_in' in session and session.get('is_admin'):
        cur = mysql.connection.cursor()

        if request.method == 'GET':
            # Fetch all managers with their assigned elections
            cur.execute("""
                SELECT U.users_id, U.username, U.contact_no, E.Election_topic
                FROM USERS U
                LEFT JOIN MANAGER_ELECTIONS ME ON U.users_id = ME.manager_id
                LEFT JOIN ELECTIONS E ON ME.election_id = E.elections_id
                WHERE U.user_role = 'manager'
            """)
            managers = cur.fetchall()

            # Fetch all elections for the form dropdown
            cur.execute("SELECT * FROM ELECTIONS")
            elections = cur.fetchall()
            cur.close()
            return render_template('assign_election.html', managers=managers, elections=elections)

        # Handle POST request for assigning an election to a manager
        if request.method == 'POST' and 'manager_id' in request.form and 'election_id' in request.form:
            manager_id = request.form['manager_id']
            election_id = request.form['election_id']
            cur.execute("INSERT INTO MANAGER_ELECTIONS (manager_id, election_id) VALUES (%s, %s)", (manager_id, election_id))
            mysql.connection.commit()
            cur.close()
            flash('Election assigned to the manager successfully!')
            return redirect(url_for('assign_election'))

    flash('Access restricted to admins only.')
    return redirect(url_for('login'))


@app.route('/delete_manager/<int:manager_id>', methods=['POST'])
def delete_manager(manager_id):
    if 'logged_in' in session and session.get('is_admin'):
        try:
            cur = mysql.connection.cursor()
            # Check if the user is a manager
            cur.execute("SELECT * FROM USERS WHERE users_id = %s AND user_role = 'manager'", (manager_id,))
            manager = cur.fetchone()
            
            if manager:
                # Delete manager record and any associated privileges
                cur.execute("DELETE FROM MANAGER_ELECTIONS WHERE manager_id = %s", (manager_id,))
                cur.execute("DELETE FROM USERS WHERE users_id = %s", (manager_id,))
                mysql.connection.commit()
                flash('Manager deleted successfully!')
            else:
                flash('Manager not found or not valid.')

            cur.close()
        except Exception as e:
            flash('Error deleting manager: ' + str(e))
    else:
        flash('Access restricted to admins only.')

    return redirect(url_for('assign_election'))
#-------------------------------------------------------------------------------------
#------------------------MANAGE CANDIDATES---------------------------------------------
@app.route('/manage_candidates', methods=['GET', 'POST'])
def manage_candidates():
    if 'logged_in' in session and session.get('is_admin'):
        cur = mysql.connection.cursor()

        # Fetch all candidates with their election and party details
        cur.execute("""
            SELECT C.candidate_id, C.candidate_name, C.candidate_details, C.candidate_photo,
                   E.Election_topic, P.party_name
            FROM CANDIDATE_DETAILS C
            LEFT JOIN ELECTIONS E ON C.election_id = E.elections_id
            LEFT JOIN PARTIES P ON C.party_id = P.party_id
        """)
        candidates = cur.fetchall()
        cur.close()

        return render_template('manage_candidates.html', candidates=candidates)

    flash('Access restricted to admins only.')
    return redirect(url_for('login'))

@app.route('/delete_candidate/<int:candidate_id>', methods=['POST'])
def delete_candidate(candidate_id):
    if 'logged_in' in session and (session.get('is_admin') or session.get('user_role') == 'manager'):
        try:
            cur = mysql.connection.cursor()
            cur.execute("DELETE FROM CANDIDATE_DETAILS WHERE candidate_id = %s", (candidate_id,))
            mysql.connection.commit()
            cur.close()
            flash('Candidate deleted successfully!')
        except Exception as e:
            flash('Error deleting candidate: ' + str(e))
    else:
        flash('Access restricted to admins only.')
    
    return redirect(url_for('manage_candidates'))

@app.route('/update_candidate/<int:candidate_id>', methods=['GET', 'POST'])
def update_candidate(candidate_id):
    if 'logged_in' in session and session.get('is_admin'):
        cur = mysql.connection.cursor()

        # Get the current candidate details
        cur.execute("SELECT * FROM CANDIDATE_DETAILS WHERE candidate_id = %s", (candidate_id,))
        candidate = cur.fetchone()

        if request.method == 'POST':
            candidate_name = request.form['candidate_name']
            candidate_details = request.form['candidate_details']
            party_id = request.form['party_id']
            
            # Handle the image upload
            new_image_filename = None
            if 'candidate_photo' in request.files:
                file = request.files['candidate_photo']
                if file and allowed_file(file.filename):
                    # Secure the filename and save the file
                    new_image_filename = secure_filename(file.filename)

                # Ensure the upload folder exists
                    upload_folder = os.path.join('static', 'uploads', 'candidate_photos')
                    if not os.path.exists(upload_folder):
                        os.makedirs(upload_folder)

                    # Save the file in the 'uploads/candidate_photos' folder
                    file.save(os.path.join(upload_folder, new_image_filename))

            # Update the candidate in the database
            if new_image_filename:
                cur.execute("""
                    UPDATE CANDIDATE_DETAILS 
                    SET candidate_name = %s, candidate_details = %s, candidate_photo = %s, party_id = %s 
                    WHERE candidate_id = %s
                """, (candidate_name, candidate_details, new_image_filename, party_id, candidate_id))
            else:
                # No image uploaded, update without changing the photo
                cur.execute("""
                    UPDATE CANDIDATE_DETAILS 
                    SET candidate_name = %s, candidate_details = %s, party_id = %s 
                    WHERE candidate_id = %s
                """, (candidate_name, candidate_details, party_id, candidate_id))

            mysql.connection.commit()
            cur.close()
            flash('Candidate updated successfully!')
            return redirect(url_for('manage_candidates'))  # Redirect to the manage candidates page
        
        # Fetch party details for the dropdown
        cur.execute("SELECT party_id, party_name FROM PARTIES")
        parties = cur.fetchall()

        cur.close()
        return render_template('update_candidate.html', candidate=candidate, parties=parties)

    flash('You do not have permission to access this page.')
    return redirect(url_for('login'))


# Route for serving images
@app.route('/uploads/candidate_photos/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/add_candidate', methods=['GET', 'POST'])
def add_candidate():
    if 'logged_in' in session and session.get('is_admin'):
        if request.method == 'POST':
            candidate_name = request.form['candidate_name']
            candidate_details = request.form['candidate_details']
            party_id = request.form['party_id']
            election_id = request.form['election_id']
            candidate_photo = request.form['candidate_photo']  # Handle file upload

            cur = mysql.connection.cursor()
            cur.execute("""
                INSERT INTO CANDIDATE_DETAILS (candidate_name, candidate_details, candidate_photo, party_id, election_id) 
                VALUES (%s, %s, %s, %s, %s)
            """, (candidate_name, candidate_details, candidate_photo, party_id, election_id))
            mysql.connection.commit()
            cur.close()

            flash('Candidate added successfully!')
            return redirect(url_for('admin_dashboard'))
        return render_template('add_candidate.html')
    
    flash('You do not have permission to access this page.')
    return redirect(url_for('login'))

#--------------------------\ MANAGE PARTIES |---------------------------------------------------

@app.route('/manage_parties', methods=['GET', 'POST'])
def manage_parties():
    if 'logged_in' in session and session.get('is_admin'):
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM PARTIES")
        parties = cur.fetchall()
        cur.close()
        
        return render_template('manage_parties.html', parties=parties)
    
    flash('You do not have permission to access this page.')
    return redirect(url_for('login'))

@app.route('/add_party', methods=['GET', 'POST'])
def add_party():
    if 'logged_in' in session and session.get('is_admin'):
        if request.method == 'POST':
            party_name = request.form['party_name']
            party_details = request.form['party_details']

            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO PARTIES (party_name, party_details) VALUES (%s, %s)", 
                        (party_name, party_details))
            mysql.connection.commit()
            cur.close()

            flash('Party added successfully!')
            return redirect(url_for('admin_dashboard'))

        return render_template('add_party.html')
    
    flash('You do not have permission to access this page.')
    return redirect(url_for('login'))

@app.route('/update_party/<int:party_id>', methods=['GET', 'POST'])
def update_party(party_id):
    if 'logged_in' not in session or not session.get('is_admin'):
        flash('Unauthorized access.')
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    # Fetch the current party details
    cur.execute("SELECT * FROM PARTIES WHERE party_id = %s", (party_id,))
    party = cur.fetchone()

    if not party:
        flash('Party not found.')
        return redirect(url_for('manage_parties'))

    if request.method == 'POST':
        party_name = request.form['party_name']

        # Handle the logo upload
        new_logo_filename = None
        if 'party_logo' in request.files:
            file = request.files['party_logo']
            if file and allowed_file(file.filename):
                # Secure the filename
                new_logo_filename = secure_filename(file.filename)

                # Ensure the upload folder exists
                upload_folder = os.path.join('static', 'uploads', 'party_logos')
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)

                # Save the file in the 'uploads/party_logos' folder
                file.save(os.path.join(upload_folder, new_logo_filename))

        # Update the party in the database
        if new_logo_filename:
            cur.execute("""
                UPDATE PARTIES 
                SET party_name = %s, party_logo = %s 
                WHERE party_id = %s
            """, (party_name, new_logo_filename, party_id))
        else:
            # No logo uploaded, update without changing the current logo
            cur.execute("""
                UPDATE PARTIES 
                SET party_name = %s 
                WHERE party_id = %s
            """, (party_name, party_id))

        mysql.connection.commit()
        cur.close()
        flash('Party updated successfully.')
        return redirect(url_for('manage_parties'))

    cur.close()
    return render_template('update_party.html', party=party)




@app.route('/delete_party/<int:party_id>', methods=['GET', 'POST'])
def delete_party(party_id):
    if 'logged_in' in session and session.get('is_admin'):
        cur = mysql.connection.cursor()
        
        # Fetch party details to display in the confirmation form
        cur.execute("SELECT * FROM PARTIES WHERE party_id = %s", (party_id,))
        party = cur.fetchone()

        if request.method == 'POST':
            if request.form.get('_method') == 'DELETE':  # Handle the DELETE method
                try:
                    cur.execute("DELETE FROM PARTIES WHERE party_id = %s", (party_id,))
                    mysql.connection.commit()
                    flash('Party deleted successfully, along with associated candidates!')
                except Exception as e:
                    flash(f'Error deleting party: {str(e)}')

                return redirect(url_for('manage_parties'))
        
        return render_template('delete_party.html', party=party)
    else:
        flash('Access restricted to admins only.')
        return redirect(url_for('manage_parties'))

#------------------------------------------VIEW STATISTICS----------------------------------------

@app.route('/statistics/overview')
def statistics_overview():
    if 'logged_in' in session:
        cur = mysql.connection.cursor()

        # Get total number of candidates
        cur.execute("SELECT GetTotalCandidates();")
        result = cur.fetchone()
        total_candidates = result['GetTotalCandidates()'] if result else 0

        # Get total number of parties
        cur.execute("SELECT GetTotalParties();")
        result = cur.fetchone()
        total_parties = result['GetTotalParties()'] if result else 0

        cur.execute("""
            SELECT e.elections_id, e.election_topic, e.starting_date, e.ending_date,
                   (SELECT COUNT(*)
                    FROM CANDIDATE_DETAILS c
                    WHERE c.election_id = e.elections_id) AS candidate_count
            FROM ELECTIONS e
        """)
        elections_with_candidates = cur.fetchall()

        # Fetch total votes by party with party names
        cur.execute("""
            SELECT party_id, party_name, GetTotalVotesByParty(party_id) AS votes 
            FROM PARTIES
        """)
        votes_by_party = cur.fetchall()

        # Fetch election ID, election name, election topic, and top candidates in each election
        cur.execute("""
            SELECT e.elections_id AS election_id, e.election_topic, e.election_topic,
                GetTopCandidateInElection(e.elections_id) AS top_candidates
            FROM ELECTIONS e
        """)
        top_candidates = cur.fetchall()  # Now includes election_name, election_topic, and top candidates

        cur.close()

        return render_template('statistics/overview.html', 
                            total_candidates=total_candidates, 
                            total_parties=total_parties, 
                            elections_with_candidates=elections_with_candidates,
                            votes_by_party=votes_by_party, 
                            top_candidates=top_candidates)



#--------------------------------------------------------------------------

@app.route('/manager_dashboard')
def manager_dashboard():
    if 'logged_in' in session and session.get('user_role') == 'manager':
        user_id = session['user_id']
        cur = mysql.connection.cursor()

        # Fetch elections assigned to this manager
        cur.execute("""
            SELECT E.elections_id, E.Election_topic, E.starting_date, E.ending_date, E.status
            FROM ELECTIONS E
            JOIN MANAGER_ELECTIONS ME ON E.elections_id = ME.election_id
            WHERE ME.manager_id = %s
        """, (user_id,))
        managed_elections = cur.fetchall()
        cur.close()

        return render_template('manager_dashboard.html', elections=managed_elections)
    else:
        flash('Access restricted to managers only.')
        return redirect(url_for('login'))


@app.route('/edit_election/<int:election_id>', methods=['GET', 'POST'])
def edit_election(election_id):
    if 'logged_in' in session and session.get('user_role') == 'manager':
        user_id = session['user_id']
        cur = mysql.connection.cursor()

        # Check if the manager is allowed to access this election
        cur.execute("""
            SELECT * FROM MANAGER_ELECTIONS 
            WHERE manager_id = %s AND election_id = %s
        """, (user_id, election_id))
        assigned_election = cur.fetchone()

        if not assigned_election:
            flash('You do not have permission to edit this election.')
            return redirect(url_for('manager_dashboard'))

        # Handle form submission
        if request.method == 'POST':
            election_topic = request.form['election_topic']
            starting_date = request.form['starting_date']
            ending_date = request.form['ending_date']
            status = request.form['status']

            # Update election details
            cur.execute("""
                UPDATE ELECTIONS
                SET Election_topic = %s, starting_date = %s, ending_date = %s, status = %s
                WHERE elections_id = %s
            """, (election_topic, starting_date, ending_date, status, election_id))
            mysql.connection.commit()
            flash('Election details updated successfully!')
            cur.close()
            return redirect(url_for('manager_dashboard'))

        # Fetch existing election details for the form
        cur.execute("SELECT * FROM ELECTIONS WHERE elections_id = %s", (election_id,))
        election_details = cur.fetchone()
        cur.close()
        return render_template('edit_election.html', election=election_details)
    else:
        flash('Access restricted to managers only.')
        return redirect(url_for('login'))

@app.route('/manager/manage_candidates/<int:election_id>', methods=['GET', 'POST'])
def manage_candidates_manager(election_id):
    if 'logged_in' in session and session.get('user_role') == 'manager':
        user_id = session['user_id']
        cur = mysql.connection.cursor()

        # Check if the manager is allowed to access this election
        cur.execute("""
            SELECT * FROM MANAGER_ELECTIONS 
            WHERE manager_id = %s AND election_id = %s
        """, (user_id, election_id))
        assigned_election = cur.fetchone()

        if not assigned_election:
            flash('You do not have permission to manage candidates for this election.')
            return redirect(url_for('manager_dashboard'))

        # Handle adding new candidates
        if request.method == 'POST' and 'add_candidate' in request.form:
            candidate_name = request.form['candidate_name']
            candidate_details = request.form['candidate_details']
            candidate_photo = request.form['candidate_photo']
            party_id = request.form['party_id']

            cur.execute("""
                INSERT INTO CANDIDATE_DETAILS (election_id, candidate_name, candidate_details, candidate_photo, party_id, inserted_by, inserted_from)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (election_id, candidate_name, candidate_details, candidate_photo, party_id, user_id, 'Manager Portal'))
            mysql.connection.commit()
            flash('Candidate added successfully!')

        # Fetch existing candidates for the election
        cur.execute("SELECT * FROM CANDIDATE_DETAILS WHERE election_id = %s", (election_id,))
        candidates = cur.fetchall()
        cur.close()
        return render_template('manage_candidates_manager.html', election_id=election_id, candidates=candidates)
    else:
        flash('Access restricted to managers only.')
        return redirect(url_for('login'))



@app.route('/view_voter_participation/<int:election_id>')
def view_voter_participation(election_id):
    if 'logged_in' in session and session.get('user_role') == 'manager':
        user_id = session['user_id']
        cur = mysql.connection.cursor()

        # Check if the manager is allowed to access this election
        cur.execute("""
            SELECT * FROM MANAGER_ELECTIONS 
            WHERE manager_id = %s AND election_id = %s
        """, (user_id, election_id))
        assigned_election = cur.fetchone()

        if not assigned_election:
            flash('You do not have permission to view voter participation for this election.')
            return redirect(url_for('manager_dashboard'))

        # Fetch voter participation details
        cur.execute("""
            SELECT U.username, V.vote_date, V.vote_time
            FROM VOTINGS V
            JOIN USERS U ON V.voters_id = U.users_id
            WHERE V.election_id = %s
        """, (election_id,))
        voter_participation = cur.fetchall()
        cur.close()
        return render_template('view_voter_participation.html', election_id=election_id, voters=voter_participation)
    else:
        flash('Access restricted to managers only.')
        return redirect(url_for('login'))




if __name__ == '__main__':
    app.run(debug=True)
