DROP DATABASE voting_db;
create database voting_db;
use voting_db;

CREATE TABLE USERS (
    users_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50),
    contact_no VARCHAR(20),
    password VARCHAR(255),
    user_role VARCHAR(20),
    is_admin BOOLEAN
);

CREATE TABLE PARTIES (
    party_id INT AUTO_INCREMENT PRIMARY KEY,
    party_name VARCHAR(100),
    party_logo VARCHAR(255),
    inserted_by INT,
    inserted_on DATETIME
);

CREATE TABLE ELECTIONS (
    elections_id INT AUTO_INCREMENT PRIMARY KEY,
    Election_topic VARCHAR(255),
    no_of_candidates INT,
    starting_date DATE,
    ending_Date DATE,
    status VARCHAR(20),
    inserted_by INT,
    inserted_on DATETIME
);

CREATE TABLE ADMIN_ROLES (
    admin_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    role_description VARCHAR(255),
    FOREIGN KEY (user_id) REFERENCES USERS(users_id)
);

CREATE TABLE CANDIDATE_DETAILS (
    candidate_id INT AUTO_INCREMENT PRIMARY KEY,
    election_id INT,
    candidate_name VARCHAR(100),
    candidate_details TEXT,
    candidate_photo VARCHAR(255),
    party_id INT,
    inserted_by INT,
    inserted_from VARCHAR(50),
    FOREIGN KEY (election_id) REFERENCES ELECTIONS(elections_id),
    FOREIGN KEY (party_id) REFERENCES PARTIES(party_id)
);

CREATE TABLE VOTINGS (
    votes_id INT PRIMARY KEY AUTO_INCREMENT,
    election_id INT,
    voters_id INT,
    candidate_id INT,
    vote_date DATE,
    vote_time TIME,
    FOREIGN KEY (election_id) REFERENCES ELECTIONS(elections_id),
    FOREIGN KEY (voters_id) REFERENCES USERS(users_id),
    FOREIGN KEY (candidate_id) REFERENCES CANDIDATE_DETAILS(candidate_id)
);

CREATE TABLE MANAGER_ELECTIONS (
    manager_election_id INT PRIMARY KEY AUTO_INCREMENT,
    manager_id INT,
    election_id INT,
    FOREIGN KEY (manager_id) REFERENCES USERS(users_id),
    FOREIGN KEY (election_id) REFERENCES ELECTIONS(elections_id)
);
#user trigger

DELIMITER $$

CREATE TRIGGER before_candidate_delete
BEFORE DELETE ON CANDIDATE_DETAILS
FOR EACH ROW
BEGIN
    -- Delete all votes associated with the candidate
    DELETE FROM VOTINGS WHERE candidate_id = OLD.candidate_id;
END$$

DELIMITER ;

DELIMITER $$

CREATE TRIGGER before_user_delete
before DELETE ON USERS
FOR EACH ROW
BEGIN
    -- Delete votes associated with the user (if they are a voter)
    DELETE FROM VOTINGS WHERE voters_id = OLD.users_id;
    
    -- Delete candidates related to the user (if they are a party creator or candidate)
    DELETE FROM CANDIDATE_DETAILS WHERE inserted_by = OLD.users_id;
    
    -- Delete party-related information (if the user created a party)
    DELETE FROM PARTIES WHERE inserted_by = OLD.users_id;
    
    -- Delete admin role related to the user
    DELETE FROM ADMIN_ROLES WHERE user_id = OLD.users_id;
END$$

DELIMITER ;

DELIMITER //
CREATE TRIGGER after_user_update
AFTER UPDATE ON USERS
FOR EACH ROW
BEGIN
    UPDATE ADMIN_ROLES SET user_id = NEW.users_id WHERE user_id = OLD.users_id;
    UPDATE MANAGER_ELECTIONS SET manager_id = NEW.users_id WHERE manager_id = OLD.users_id;
    UPDATE VOTINGS SET voters_id = NEW.users_id WHERE voters_id = OLD.users_id;
END//

DELIMITER ;

#elections trigger
DELIMITER $$

CREATE TRIGGER before_election_delete
before DELETE ON ELECTIONS
FOR EACH ROW
BEGIN
    -- Delete all votes associated with the candidates in the election
    DELETE FROM VOTINGS WHERE election_id = OLD.elections_id;
    
    -- Delete all candidates associated with the election
    DELETE FROM CANDIDATE_DETAILS WHERE election_id = OLD.elections_id;
END$$

DELIMITER ;

-- HELLO

DELIMITER $$

CREATE TRIGGER after_election_update
AFTER UPDATE ON ELECTIONS
FOR EACH ROW
BEGIN
    UPDATE CANDIDATE_DETAILS SET election_id = NEW.elections_id WHERE election_id = OLD.elections_id;
    UPDATE VOTINGS SET election_id = NEW.elections_id WHERE election_id = OLD.elections_id;
    UPDATE MANAGER_ELECTIONS SET election_id = NEW.elections_id WHERE election_id = OLD.elections_id;
END$$

DELIMITER ;

#parties trigger
DELIMITER $$

CREATE TRIGGER berfore_party_delete
BEFORE DELETE ON PARTIES
FOR EACH ROW
BEGIN
    -- Delete all candidates associated with the party in CANDIDATE_DETAILS
    DELETE FROM CANDIDATE_DETAILS WHERE party_id = OLD.party_id;
END$$

DELIMITER ;

DELIMITER //

CREATE TRIGGER after_party_update
AFTER UPDATE ON PARTIES
FOR EACH ROW
BEGIN
    UPDATE CANDIDATE_DETAILS 
    SET party_id = NEW.party_id 
    WHERE party_id = OLD.party_id;
END;
//
DELIMITER ;





DELIMITER //

CREATE FUNCTION GetTotalCandidates()
RETURNS INT
DETERMINISTIC
BEGIN
    DECLARE total_candidates INT;
    SELECT COUNT(*) INTO total_candidates FROM CANDIDATE_DETAILS;
    RETURN total_candidates;
END;
//

DELIMITER ;

select GetTotalCandidates();

-- Total Number of Parties Function:

DELIMITER //

CREATE FUNCTION GetTotalParties()
RETURNS INT
DETERMINISTIC
BEGIN
    DECLARE total_parties INT;
    SELECT COUNT(*) INTO total_parties FROM PARTIES;
    RETURN total_parties;
END;
//

DELIMITER ;

-- Total Votes by Party Function:

DELIMITER //

CREATE FUNCTION GetTotalVotesByParty(party_id INT)
RETURNS INT
DETERMINISTIC
BEGIN
    DECLARE total_votes INT;
    SELECT COUNT(*) INTO total_votes 
    FROM VOTINGS v 
    JOIN CANDIDATE_DETAILS cd ON v.candidate_id = cd.candidate_id
    WHERE cd.party_id = party_id;
    RETURN total_votes;
END;
//

DELIMITER ;
-- Total Votes by Candidate Function:
DELIMITER //

CREATE FUNCTION GetTotalVotesByCandidate(candidate_id INT)
RETURNS INT
DETERMINISTIC
BEGIN
    DECLARE total_votes INT;
    SELECT COUNT(*) INTO total_votes 
    FROM VOTINGS 
    WHERE candidate_id = candidate_id;
    RETURN total_votes;
END;
//

DELIMITER ;

-- Top Candidate in Each Election Function:
DELIMITER //

CREATE FUNCTION GetTopCandidateInElection(election_id INT)
RETURNS VARCHAR(255)
DETERMINISTIC
BEGIN
    DECLARE candidate_name VARCHAR(255);
    
    SELECT cd.candidate_name
    INTO candidate_name
    FROM CANDIDATE_DETAILS cd
    WHERE cd.election_id = election_id
    ORDER BY (
        SELECT COUNT(*) 
        FROM VOTINGS v 
        WHERE v.candidate_id = cd.candidate_id
    ) DESC
    LIMIT 1;

    RETURN candidate_name;
END;
//

DELIMITER ;

select GetTopCandidateInElection(4);
-- Admin Users and Roles

INSERT INTO USERS (users_id, username, contact_no, password, user_role, is_admin) VALUES
(1, 'superadmin', '1234567890', 'hash_pwd1', 'admin', TRUE),
(2, 'techadmin', '1234567891', 'hash_pwd2', 'admin', TRUE),
(3, 'manager1', '2345678901', 'hash_mgr1', 'manager', FALSE),
(4, 'manager2', '2345678902', 'hash_mgr2', 'manager', FALSE),
(5, 'manager3', '2345678903', 'hash_mgr3', 'manager', FALSE),
(6, 'manager4', '2345678904', 'hash_mgr4', 'manager', FALSE);

-- Voter Users (20 voters)
INSERT INTO USERS (users_id, username, contact_no, password, user_role, is_admin) VALUES
(7, 'voter1', '3456789001', 'hash_v1', 'voter', FALSE),
(8, 'voter2', '3456789002', 'hash_v2', 'voter', FALSE),
(9, 'voter3', '3456789003', 'hash_v3', 'voter', FALSE),
(10, 'voter4', '3456789004', 'hash_v4', 'voter', FALSE),
(11, 'voter5', '3456789005', 'hash_v5', 'voter', FALSE),
(12, 'voter6', '3456789006', 'hash_v6', 'voter', FALSE),
(13, 'voter7', '3456789007', 'hash_v7', 'voter', FALSE),
(14, 'voter8', '3456789008', 'hash_v8', 'voter', FALSE),
(15, 'voter9', '3456789009', 'hash_v9', 'voter', FALSE),
(16, 'voter10', '3456789010', 'hash_v10', 'voter', FALSE),
(17, 'voter11', '3456789011', 'hash_v11', 'voter', FALSE),
(18, 'voter12', '3456789012', 'hash_v12', 'voter', FALSE),
(19, 'voter13', '3456789013', 'hash_v13', 'voter', FALSE),
(20, 'voter14', '3456789014', 'hash_v14', 'voter', FALSE),
(21, 'voter15', '3456789015', 'hash_v15', 'voter', FALSE),
(22, 'voter16', '3456789016', 'hash_v16', 'voter', FALSE),
(23, 'voter17', '3456789017', 'hash_v17', 'voter', FALSE),
(24, 'voter18', '3456789018', 'hash_v18', 'voter', FALSE),
(25, 'voter19', '3456789019', 'hash_v19', 'voter', FALSE),
(26, 'voter20', '3456789020', 'hash_v20', 'voter', FALSE);

-- Admin Roles
INSERT INTO ADMIN_ROLES (admin_id, user_id, role_description) VALUES
(1, 1, 'Super Administrator'),
(2, 2, 'Technical Administrator');

-- Political Parties (12 parties)
INSERT INTO PARTIES (party_id, party_name, party_logo, inserted_by, inserted_on) VALUES
(1, 'Progressive Party', 'progressive_logo.png', 1, NOW()),
(2, 'Conservative Alliance', 'conservative_logo.png', 1, NOW()),
(3, 'Green Initiative', 'green_logo.png', 1, NOW()),
(4, 'Workers United', 'workers_logo.png', 1, NOW()),
(5, 'Democratic Front', 'democratic_logo.png', 1, NOW()),
(6, 'Reform Movement', 'reform_logo.png', 1, NOW()),
(7, 'Liberty Party', 'liberty_logo.png', 1, NOW()),
(8, 'Unity Coalition', 'unity_logo.png', 1, NOW()),
(9, 'Future Alliance', 'future_logo.png', 1, NOW()),
(10, 'Peoples Choice', 'peoples_logo.png', 1, NOW()),
(11, 'National Progress', 'national_logo.png', 1, NOW()),
(12, 'Citizens First', 'citizens_logo.png', 1, NOW());

-- Elections
INSERT INTO ELECTIONS (elections_id, Election_topic, no_of_candidates, starting_date, ending_Date, status, inserted_by, inserted_on) VALUES
(1, 'Presidential Election 2024', 3, '2024-11-01', '2024-11-03', 'Upcoming', 3, NOW()),
(2, 'Senate Election 2024', 3, '2024-12-01', '2024-12-03', 'Upcoming', 4, NOW()),
(3, 'Gubernatorial Election 2024', 3, '2024-10-15', '2024-10-17', 'Upcoming', 5, NOW()),
(4, 'City Council Election 2024', 3, '2024-09-15', '2024-09-17', 'Upcoming', 6, NOW());

-- Candidates (1 per party, 3 parties per election)
INSERT INTO CANDIDATE_DETAILS (candidate_id, election_id, candidate_name, candidate_details, candidate_photo, party_id, inserted_by, inserted_from) VALUES
-- Presidential Election Candidates
(1, 1, 'John Smith', 'Experienced leader with 20 years in public service', 'john_smith.jpg', 1, 1, 'Admin Panel'),
(2, 1, 'Mary Johnson', 'Former State Governor', 'mary_johnson.jpg', 2, 1, 'Admin Panel'),
(3, 1, 'Robert Wilson', 'Business leader and philanthropist', 'robert_wilson.jpg', 3, 1, 'Admin Panel'),

-- Senate Election Candidates
(4, 2, 'Sarah Brown', 'Legal expert and civil rights advocate', 'sarah_brown.jpg', 4, 1, 'Admin Panel'),
(5, 2, 'Michael Lee', 'Economic policy specialist', 'michael_lee.jpg', 5, 1, 'Admin Panel'),
(6, 2, 'Jennifer Davis', 'Environmental activist', 'jennifer_davis.jpg', 6, 1, 'Admin Panel'),

-- Gubernatorial Election Candidates
(7, 3, 'David Miller', 'Former Mayor', 'david_miller.jpg', 7, 1, 'Admin Panel'),
(8, 3, 'Lisa Anderson', 'State Senator', 'lisa_anderson.jpg', 8, 1, 'Admin Panel'),
(9, 3, 'James Wilson', 'Business executive', 'james_wilson.jpg', 9, 1, 'Admin Panel'),

-- City Council Election Candidates
(10, 4, 'Patricia Moore', 'Community organizer', 'patricia_moore.jpg', 10, 1, 'Admin Panel'),
(11, 4, 'Thomas Wright', 'Urban planning expert', 'thomas_wright.jpg', 11, 1, 'Admin Panel'),
(12, 4, 'Susan Taylor', 'Education advocate', 'susan_taylor.jpg', 12, 1, 'Admin Panel');

-- Select statements to verify data
SELECT * FROM ADMIN_ROLES;
SELECT * FROM USERS;
SELECT * FROM PARTIES;
SELECT * FROM ELECTIONS;
SELECT * FROM CANDIDATE_DETAILS;
SELECT * FROM VOTINGS;
select * from MANAGER_ELECTIONS;



