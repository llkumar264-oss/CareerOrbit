-- Initial PostgreSQL schema; generated from app/models.py.
-- Empty database only. Review and version migrations for upgrades.

CREATE TABLE users (
	id VARCHAR(36) NOT NULL,
	email VARCHAR(320) NOT NULL,
	password_hash TEXT NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (email)
);

CREATE TABLE sessions (
	token VARCHAR(64) NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (token),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_sessions_user_id ON sessions (user_id);

CREATE TABLE user_profiles (
	user_id VARCHAR(36) NOT NULL,
	data JSON NOT NULL,
	confirmed BOOLEAN NOT NULL,
	PRIMARY KEY (user_id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE resume_files (
	id VARCHAR(36) NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	name VARCHAR NOT NULL,
	filename VARCHAR NOT NULL,
	path VARCHAR NOT NULL,
	mime VARCHAR NOT NULL,
	sha256 VARCHAR NOT NULL,
	text TEXT NOT NULL,
	skills JSON NOT NULL,
	approved BOOLEAN NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_resume_files_user_id ON resume_files (user_id);

CREATE TABLE campaigns (
	id VARCHAR(36) NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	name VARCHAR NOT NULL,
	preferences JSON NOT NULL,
	status VARCHAR NOT NULL,
	revision INTEGER NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_campaigns_user_id ON campaigns (user_id);

CREATE TABLE contacts (
	id VARCHAR(36) NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	company_key VARCHAR NOT NULL,
	email VARCHAR NOT NULL,
	source_url VARCHAR NOT NULL,
	verification VARCHAR NOT NULL,
	role VARCHAR NOT NULL,
	checked_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (user_id, email),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE mailboxes (
	id VARCHAR(36) NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	provider VARCHAR NOT NULL,
	address VARCHAR NOT NULL,
	tokens TEXT NOT NULL,
	read_enabled BOOLEAN NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (user_id, provider),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE oauth_states (
	state VARCHAR(128) NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	provider VARCHAR NOT NULL,
	read_enabled BOOLEAN NOT NULL,
	verifier VARCHAR NOT NULL,
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (state),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE suppression_list (
	id VARCHAR(36) NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	email VARCHAR NOT NULL,
	reason VARCHAR NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (user_id, email),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE audit_logs (
	id VARCHAR(36) NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	action VARCHAR NOT NULL,
	details JSON NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_audit_logs_user_id ON audit_logs (user_id);

CREATE TABLE api_usage (
	id VARCHAR(36) NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	provider VARCHAR NOT NULL,
	calls INTEGER NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE notifications (
	id VARCHAR(36) NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	text VARCHAR NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE opportunity_listings (
	id VARCHAR(36) NOT NULL,
	campaign_id VARCHAR(36) NOT NULL,
	source VARCHAR NOT NULL,
	external_id VARCHAR NOT NULL,
	company VARCHAR NOT NULL,
	company_key VARCHAR NOT NULL,
	title VARCHAR NOT NULL,
	url TEXT NOT NULL,
	description TEXT NOT NULL,
	location VARCHAR NOT NULL,
	classification VARCHAR NOT NULL,
	data JSON NOT NULL,
	score INTEGER NOT NULL,
	explanation JSON NOT NULL,
	eligible BOOLEAN NOT NULL,
	discovered_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	verified_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (campaign_id, source, external_id),
	FOREIGN KEY(campaign_id) REFERENCES campaigns (id) ON DELETE CASCADE
);

CREATE INDEX ix_opportunity_listings_company_key ON opportunity_listings (company_key);

CREATE INDEX ix_opportunity_campaign_score ON opportunity_listings (campaign_id, score);

CREATE TABLE campaign_approvals (
	id VARCHAR(36) NOT NULL,
	campaign_id VARCHAR(36) NOT NULL,
	revision INTEGER NOT NULL,
	scope_hash VARCHAR NOT NULL,
	draft_ids JSON NOT NULL,
	max_messages INTEGER NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(campaign_id) REFERENCES campaigns (id) ON DELETE CASCADE
);

CREATE INDEX ix_campaign_approvals_campaign_id ON campaign_approvals (campaign_id);

CREATE TABLE scheduled_research (
	campaign_id VARCHAR(36) NOT NULL,
	interval_hours INTEGER NOT NULL,
	next_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	enabled BOOLEAN NOT NULL,
	last_error VARCHAR NOT NULL,
	PRIMARY KEY (campaign_id),
	FOREIGN KEY(campaign_id) REFERENCES campaigns (id) ON DELETE CASCADE
);

CREATE TABLE email_drafts (
	id VARCHAR(36) NOT NULL,
	campaign_id VARCHAR(36) NOT NULL,
	opportunity_id VARCHAR(36) NOT NULL,
	contact_id VARCHAR(36) NOT NULL,
	resume_id VARCHAR(36) NOT NULL,
	subject VARCHAR NOT NULL,
	body TEXT NOT NULL,
	status VARCHAR NOT NULL,
	validation JSON NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (campaign_id, opportunity_id),
	FOREIGN KEY(campaign_id) REFERENCES campaigns (id) ON DELETE CASCADE,
	FOREIGN KEY(opportunity_id) REFERENCES opportunity_listings (id) ON DELETE CASCADE,
	FOREIGN KEY(contact_id) REFERENCES contacts (id) ON DELETE CASCADE,
	FOREIGN KEY(resume_id) REFERENCES resume_files (id) ON DELETE RESTRICT
);

CREATE TABLE applications (
	id VARCHAR(36) NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	opportunity_id VARCHAR(36) NOT NULL,
	status VARCHAR NOT NULL,
	channel VARCHAR NOT NULL,
	notes TEXT NOT NULL,
	interview_at TIMESTAMP WITHOUT TIME ZONE,
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (user_id, opportunity_id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	FOREIGN KEY(opportunity_id) REFERENCES opportunity_listings (id) ON DELETE CASCADE
);

CREATE TABLE sending_queue (
	id VARCHAR(36) NOT NULL,
	draft_id VARCHAR(36) NOT NULL,
	approval_id VARCHAR(36) NOT NULL,
	mailbox_id VARCHAR(36) NOT NULL,
	status VARCHAR NOT NULL,
	attempts INTEGER NOT NULL,
	next_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	error VARCHAR NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (draft_id),
	FOREIGN KEY(draft_id) REFERENCES email_drafts (id) ON DELETE CASCADE,
	FOREIGN KEY(approval_id) REFERENCES campaign_approvals (id) ON DELETE CASCADE,
	FOREIGN KEY(mailbox_id) REFERENCES mailboxes (id) ON DELETE CASCADE
);

CREATE INDEX ix_sending_queue_status ON sending_queue (status);

CREATE TABLE email_messages (
	id VARCHAR(36) NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	campaign_id VARCHAR(36) NOT NULL,
	draft_id VARCHAR(36) NOT NULL,
	company_key VARCHAR NOT NULL,
	recipient VARCHAR NOT NULL,
	provider_id VARCHAR NOT NULL,
	thread_id VARCHAR NOT NULL,
	status VARCHAR NOT NULL,
	sent_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (draft_id),
	UNIQUE (user_id, company_key),
	UNIQUE (user_id, recipient),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	FOREIGN KEY(campaign_id) REFERENCES campaigns (id) ON DELETE CASCADE,
	FOREIGN KEY(draft_id) REFERENCES email_drafts (id) ON DELETE CASCADE
);

CREATE INDEX ix_email_messages_campaign_id ON email_messages (campaign_id);

CREATE INDEX ix_email_messages_user_id ON email_messages (user_id);

CREATE TABLE replies (
	id VARCHAR(36) NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	mailbox_id VARCHAR(36) NOT NULL,
	message_id VARCHAR(36),
	provider_id VARCHAR NOT NULL,
	category VARCHAR NOT NULL,
	body TEXT NOT NULL,
	received_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (mailbox_id, provider_id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	FOREIGN KEY(mailbox_id) REFERENCES mailboxes (id) ON DELETE CASCADE,
	FOREIGN KEY(message_id) REFERENCES email_messages (id) ON DELETE SET NULL
);

CREATE TABLE follow_ups (
	id VARCHAR(36) NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	message_id VARCHAR(36) NOT NULL,
	mailbox_id VARCHAR(36) NOT NULL,
	campaign_revision INTEGER NOT NULL,
	subject VARCHAR NOT NULL,
	body TEXT NOT NULL,
	status VARCHAR NOT NULL,
	attempts INTEGER NOT NULL,
	next_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	provider_id VARCHAR NOT NULL,
	sent_at TIMESTAMP WITHOUT TIME ZONE,
	error VARCHAR NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	UNIQUE (message_id),
	FOREIGN KEY(message_id) REFERENCES email_messages (id) ON DELETE CASCADE,
	FOREIGN KEY(mailbox_id) REFERENCES mailboxes (id) ON DELETE CASCADE
);

CREATE INDEX ix_follow_ups_status ON follow_ups (status);

CREATE INDEX ix_follow_ups_user_id ON follow_ups (user_id);
