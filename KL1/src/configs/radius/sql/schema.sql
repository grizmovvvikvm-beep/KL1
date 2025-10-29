-- RADIUS Database Schema for KursLight VPN
-- PostgreSQL version

-- RADIUS check table for user authentication
CREATE TABLE radcheck (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) NOT NULL DEFAULT '',
    attribute VARCHAR(64) NOT NULL DEFAULT '',
    op CHAR(2) NOT NULL DEFAULT '==',
    value VARCHAR(253) NOT NULL DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- RADIUS reply table for user authorization
CREATE TABLE radreply (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) NOT NULL DEFAULT '',
    attribute VARCHAR(64) NOT NULL DEFAULT '',
    op CHAR(2) NOT NULL DEFAULT '=',
    value VARCHAR(253) NOT NULL DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- RADIUS groups
CREATE TABLE radusergroup (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) NOT NULL DEFAULT '',
    groupname VARCHAR(64) NOT NULL DEFAULT '',
    priority INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- RADIUS group check
CREATE TABLE radgroupcheck (
    id SERIAL PRIMARY KEY,
    groupname VARCHAR(64) NOT NULL DEFAULT '',
    attribute VARCHAR(64) NOT NULL DEFAULT '',
    op CHAR(2) NOT NULL DEFAULT '==',
    value VARCHAR(253) NOT NULL DEFAULT ''
);

-- RADIUS group reply
CREATE TABLE radgroupreply (
    id SERIAL PRIMARY KEY,
    groupname VARCHAR(64) NOT NULL DEFAULT '',
    attribute VARCHAR(64) NOT NULL DEFAULT '',
    op CHAR(2) NOT NULL DEFAULT '=',
    value VARCHAR(253) NOT NULL DEFAULT ''
);

-- RADIUS accounting
CREATE TABLE radacct (
    radacctid BIGSERIAL PRIMARY KEY,
    acctsessionid VARCHAR(64) NOT NULL DEFAULT '',
    acctuniqueid VARCHAR(32) NOT NULL UNIQUE,
    username VARCHAR(64) NOT NULL DEFAULT '',
    groupname VARCHAR(64) DEFAULT '',
    realm VARCHAR(64) DEFAULT '',
    nasipaddress INET NOT NULL,
    nasportid VARCHAR(15) DEFAULT NULL,
    nasporttype VARCHAR(32) DEFAULT NULL,
    acctstarttime TIMESTAMP WITH TIME ZONE NULL DEFAULT NULL,
    acctupdatetime TIMESTAMP WITH TIME ZONE NULL DEFAULT NULL,
    acctstoptime TIMESTAMP WITH TIME ZONE NULL DEFAULT NULL,
    acctinterval BIGINT DEFAULT NULL,
    acctsessiontime BIGINT DEFAULT NULL,
    acctauthentic VARCHAR(32) DEFAULT NULL,
    connectinfo_start VARCHAR(50) DEFAULT NULL,
    connectinfo_stop VARCHAR(50) DEFAULT NULL,
    acctinputoctets BIGINT DEFAULT NULL,
    acctoutputoctets BIGINT DEFAULT NULL,
    calledstationid VARCHAR(50) NOT NULL DEFAULT '',
    callingstationid VARCHAR(50) NOT NULL DEFAULT '',
    acctterminatecause VARCHAR(32) NOT NULL DEFAULT '',
    servicetype VARCHAR(32) DEFAULT NULL,
    framedprotocol VARCHAR(32) DEFAULT NULL,
    framedipaddress INET NOT NULL,
    framedipv6address INET DEFAULT NULL,
    framedipv6prefix INET DEFAULT NULL,
    framedinterfaceid VARCHAR(64) DEFAULT NULL,
    delegatedipv6prefix INET DEFAULT NULL
);

-- Post-authentication logging
CREATE TABLE radpostauth (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) NOT NULL DEFAULT '',
    pass VARCHAR(64) NOT NULL DEFAULT '',
    reply VARCHAR(32) NOT NULL DEFAULT '',
    authdate TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    client_ip INET DEFAULT NULL,
    nas_identifier VARCHAR(64) DEFAULT NULL
);

-- NAS clients table
CREATE TABLE nas (
    id SERIAL PRIMARY KEY,
    nasname VARCHAR(128) NOT NULL,
    shortname VARCHAR(32),
    type VARCHAR(30) DEFAULT 'other',
    ports INTEGER,
    secret VARCHAR(60) NOT NULL DEFAULT 'secret',
    server VARCHAR(64),
    community VARCHAR(50),
    description VARCHAR(200) DEFAULT 'RADIUS Client'
);

-- Create indexes for performance
CREATE INDEX radcheck_username ON radcheck (username);
CREATE INDEX radreply_username ON radreply (username);
CREATE INDEX radusergroup_username ON radusergroup (username);
CREATE INDEX radacct_username ON radacct (username);
CREATE INDEX radacct_acctsessionid ON radacct (acctsessionid);
CREATE INDEX radacct_acctsessiontime ON radacct (acctsessiontime);
CREATE INDEX radacct_acctstarttime ON radacct (acctstarttime);
CREATE INDEX radacct_acctstoptime ON radacct (acctstoptime);
CREATE INDEX radacct_nasipaddress ON radacct (nasipaddress);
CREATE INDEX radpostauth_username ON radpostauth (username);
CREATE INDEX radpostauth_authdate ON radpostauth (authdate);

-- Insert default NAS entry
INSERT INTO nas (nasname, shortname, type, secret, description) 
VALUES ('127.0.0.1', 'localhost', 'other', 'radius_secret', 'Local RADIUS Server');

-- Insert test user
INSERT INTO radcheck (username, attribute, op, value) 
VALUES 
('testuser', 'Cleartext-Password', ':=', 'testpass'),
('admin', 'Cleartext-Password', ':=', 'admin123');

INSERT INTO radusergroup (username, groupname, priority) 
VALUES 
('testuser', 'users', 1),
('admin', 'admins', 1);

-- Insert group policies
INSERT INTO radgroupcheck (groupname, attribute, op, value) 
VALUES 
('users', 'Simultaneous-Use', ':=', '1'),
('admins', 'Simultaneous-Use', ':=', '5');

INSERT INTO radgroupreply (groupname, attribute, op, value) 
VALUES 
('users', 'Framed-Protocol', ':=', 'PPP'),
('users', 'Framed-Compression', ':=', 'Van-Jacobson-TCP-IP'),
('admins', 'Framed-Protocol', ':=', 'PPP'),
('admins', 'KursLight-VPN-User-Role', ':=', 'admin');