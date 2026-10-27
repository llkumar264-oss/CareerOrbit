import uuid
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, UniqueConstraint, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base, now

def uid(): return str(uuid.uuid4())
class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=now)
class Session(Base):
    __tablename__ = 'sessions'
    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    expires_at: Mapped[datetime]
class Profile(Base):
    __tablename__ = 'user_profiles'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    confirmed: Mapped[bool] = mapped_column(default=False)
class Resume(Base):
    __tablename__ = 'resume_files'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    name: Mapped[str]
    filename: Mapped[str]
    path: Mapped[str]
    mime: Mapped[str]
    sha256: Mapped[str]
    text: Mapped[str] = mapped_column(Text)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    approved: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=now)
class Campaign(Base):
    __tablename__ = 'campaigns'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    name: Mapped[str]
    preferences: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(default='draft')
    revision: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(default=now)
class Opportunity(Base):
    __tablename__ = 'opportunity_listings'
    __table_args__ = (UniqueConstraint('campaign_id','source','external_id'), Index('ix_opportunity_campaign_score','campaign_id','score'))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    campaign_id: Mapped[str] = mapped_column(ForeignKey('campaigns.id', ondelete='CASCADE'))
    source: Mapped[str]
    external_id: Mapped[str]
    company: Mapped[str]
    company_key: Mapped[str] = mapped_column(index=True)
    title: Mapped[str]
    url: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    location: Mapped[str] = mapped_column(default='')
    classification: Mapped[str] = mapped_column(default='A')
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    score: Mapped[int] = mapped_column(default=0)
    explanation: Mapped[dict] = mapped_column(JSON, default=dict)
    eligible: Mapped[bool] = mapped_column(default=True)
    discovered_at: Mapped[datetime] = mapped_column(default=now)
    verified_at: Mapped[datetime] = mapped_column(default=now)
class Contact(Base):
    __tablename__ = 'contacts'
    __table_args__ = (UniqueConstraint('user_id','email'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    company_key: Mapped[str]
    email: Mapped[str]
    source_url: Mapped[str]
    verification: Mapped[str] = mapped_column(default='unverified')
    role: Mapped[str] = mapped_column(default='')
    checked_at: Mapped[datetime] = mapped_column(default=now)
class Draft(Base):
    __tablename__ = 'email_drafts'
    __table_args__ = (UniqueConstraint('campaign_id','opportunity_id'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    campaign_id: Mapped[str] = mapped_column(ForeignKey('campaigns.id', ondelete='CASCADE'))
    opportunity_id: Mapped[str] = mapped_column(ForeignKey('opportunity_listings.id', ondelete='CASCADE'))
    contact_id: Mapped[str] = mapped_column(ForeignKey('contacts.id', ondelete='CASCADE'))
    resume_id: Mapped[str] = mapped_column(ForeignKey('resume_files.id', ondelete='RESTRICT'))
    subject: Mapped[str]
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(default='draft')
    validation: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(default=now)
class Approval(Base):
    __tablename__ = 'campaign_approvals'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    campaign_id: Mapped[str] = mapped_column(ForeignKey('campaigns.id', ondelete='CASCADE'), index=True)
    revision: Mapped[int]
    scope_hash: Mapped[str]
    draft_ids: Mapped[list] = mapped_column(JSON)
    max_messages: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(default=now)
class Mailbox(Base):
    __tablename__ = 'mailboxes'
    __table_args__ = (UniqueConstraint('user_id','provider'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    provider: Mapped[str]
    address: Mapped[str]
    tokens: Mapped[str] = mapped_column(Text)
    read_enabled: Mapped[bool] = mapped_column(default=False)
class OAuthState(Base):
    __tablename__ = 'oauth_states'
    state: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    provider: Mapped[str]
    read_enabled: Mapped[bool]
    verifier: Mapped[str]
    expires_at: Mapped[datetime]
class QueueJob(Base):
    __tablename__ = 'sending_queue'
    __table_args__ = (UniqueConstraint('draft_id'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    draft_id: Mapped[str] = mapped_column(ForeignKey('email_drafts.id', ondelete='CASCADE'))
    approval_id: Mapped[str] = mapped_column(ForeignKey('campaign_approvals.id', ondelete='CASCADE'))
    mailbox_id: Mapped[str] = mapped_column(ForeignKey('mailboxes.id', ondelete='CASCADE'))
    status: Mapped[str] = mapped_column(default='pending', index=True)
    attempts: Mapped[int] = mapped_column(default=0)
    next_at: Mapped[datetime] = mapped_column(default=now)
    error: Mapped[str] = mapped_column(default='')
class Message(Base):
    __tablename__ = 'email_messages'
    __table_args__ = (UniqueConstraint('draft_id'), UniqueConstraint('user_id','company_key'), UniqueConstraint('user_id','recipient'))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    campaign_id: Mapped[str] = mapped_column(ForeignKey('campaigns.id', ondelete='CASCADE'), index=True)
    draft_id: Mapped[str] = mapped_column(ForeignKey('email_drafts.id', ondelete='CASCADE'))
    company_key: Mapped[str]
    recipient: Mapped[str]
    provider_id: Mapped[str]
    thread_id: Mapped[str] = mapped_column(default='')
    status: Mapped[str] = mapped_column(default='sent')
    sent_at: Mapped[datetime] = mapped_column(default=now)
class Reply(Base):
    __tablename__ = 'replies'
    __table_args__ = (UniqueConstraint('mailbox_id','provider_id'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    mailbox_id: Mapped[str] = mapped_column(ForeignKey('mailboxes.id', ondelete='CASCADE'))
    message_id: Mapped[str | None] = mapped_column(ForeignKey('email_messages.id', ondelete='SET NULL'))
    provider_id: Mapped[str]
    category: Mapped[str]
    body: Mapped[str] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(default=now)
class Suppression(Base):
    __tablename__ = 'suppression_list'
    __table_args__ = (UniqueConstraint('user_id','email'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    email: Mapped[str]
    reason: Mapped[str]
class Application(Base):
    __tablename__ = 'applications'
    __table_args__ = (UniqueConstraint('user_id','opportunity_id'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    opportunity_id: Mapped[str] = mapped_column(ForeignKey('opportunity_listings.id', ondelete='CASCADE'))
    status: Mapped[str] = mapped_column(default='shortlisted')
    channel: Mapped[str] = mapped_column(default='portal')
    notes: Mapped[str] = mapped_column(Text, default='')
    interview_at: Mapped[datetime | None]
    updated_at: Mapped[datetime] = mapped_column(default=now)
class Audit(Base):
    __tablename__ = 'audit_logs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    action: Mapped[str]
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=now)
class Usage(Base):
    __tablename__ = 'api_usage'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    provider: Mapped[str]
    calls: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(default=now)
class ResearchSchedule(Base):
    __tablename__ = 'scheduled_research'
    campaign_id: Mapped[str] = mapped_column(ForeignKey('campaigns.id', ondelete='CASCADE'), primary_key=True)
    interval_hours: Mapped[int] = mapped_column(default=24)
    next_at: Mapped[datetime] = mapped_column(default=now)
    expires_at: Mapped[datetime]
    enabled: Mapped[bool] = mapped_column(default=True)
    last_error: Mapped[str] = mapped_column(default='')
class Notification(Base):
    __tablename__ = 'notifications'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    text: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(default=now)

class FollowUp(Base):
    __tablename__ = 'follow_ups'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    message_id: Mapped[str] = mapped_column(ForeignKey('email_messages.id', ondelete='CASCADE'), unique=True)
    mailbox_id: Mapped[str] = mapped_column(ForeignKey('mailboxes.id', ondelete='CASCADE'))
    campaign_revision: Mapped[int]
    subject: Mapped[str]
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(default='pending', index=True)
    attempts: Mapped[int] = mapped_column(default=0)
    next_at: Mapped[datetime] = mapped_column(default=now)
    provider_id: Mapped[str] = mapped_column(default='')
    sent_at: Mapped[datetime | None]
    error: Mapped[str] = mapped_column(default='')
