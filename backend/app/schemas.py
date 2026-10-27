from datetime import date
from typing import Literal
from pydantic import BaseModel, EmailStr, Field, HttpUrl, model_validator
from zoneinfo import ZoneInfo

TYPES = ['internship', 'full_time', 'part_time', 'research_internship', 'summer_internship', 'winter_internship', 'remote_internship', 'paid_internship', 'graduate_trainee', 'apprenticeship', 'contract', 'research_assistant', 'fellowship', 'entry_level']
class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)
class ProfileInput(BaseModel):
    full_name: str = Field(min_length=1, max_length=150)
    city: str = ''
    country: str = ''
    phone: str = ''
    linkedin: str = ''
    portfolio: str = ''
    status: str = ''
    available_from: str = ''
    graduation_year: int | None = None
    work_authorization: list[str] = []
    requires_sponsorship: bool = False
    education: list[dict] = []
    experiences: list[dict] = []
    projects: list[dict] = []
    skills: list[str] = []
    interests: list[str] = []
    confirmed: bool = False
class Preferences(BaseModel):
    query: str = Field(min_length=2, max_length=200)
    types: list[str] = Field(default=['internship'], min_length=1)
    locations: list[str] = []
    countries: list[str] = []
    remote: Literal['any','remote','hybrid','onsite'] = 'any'
    currency: str = Field(default='INR', pattern='^[A-Z]{3}$')
    minimum: float = Field(default=0, ge=0)
    ideal: float | None = Field(default=None, ge=0)
    maximum: float | None = Field(default=None, ge=0)
    frequency: Literal['hour','month','year'] = 'month'
    paid_only: bool = False
    allow_undisclosed: bool = True
    negotiable: bool = True
    target_companies: int = Field(default=100, ge=1, le=1000)
    initial_emails: int = Field(default=100, ge=1, le=1000)
    daily_limit: int = Field(default=15, ge=1, le=50)
    timezone: str = 'Asia/Kolkata'
    send_start_hour: int = Field(default=9, ge=0, le=23)
    send_end_hour: int = Field(default=17, ge=1, le=24)
    start_date: date | None = None
    end_date: date | None = None
    mode: Literal['draft_only','review','autopilot'] = 'draft_only'
    language: Literal['en'] = 'en'
    allow_speculative: bool = False
    blacklist: list[str] = []
    priority_companies: list[str] = []
    sources: dict[str, list[str]] = Field(default={'greenhouse':[], 'lever':[]})
    weights: dict[str,float] = Field(default={'skills':25,'role':20,'eligibility':15,'geography':15,'compensation':10,'interests':10,'evidence':5})
    monthly_api_call_cap: int = Field(default=300, ge=1, le=10000)
    follow_up_days: int = Field(default=8, ge=7, le=30)
    @model_validator(mode='after')
    def valid(self):
        ZoneInfo(self.timezone)
        if self.send_start_hour >= self.send_end_hour: raise ValueError('Sending hours must have start < end')
        if any(t not in TYPES for t in self.types): raise ValueError('Unknown opportunity type')
        if set(self.weights) != {'skills','role','eligibility','geography','compensation','interests','evidence'} or any(v < 0 for v in self.weights.values()) or abs(sum(self.weights.values())-100)>0.01: raise ValueError('Weights must total 100')
        if self.start_date and self.end_date and self.start_date > self.end_date: raise ValueError('End precedes start')
        if self.initial_emails > self.target_companies: raise ValueError('Initial emails cannot exceed company target')
        return self
class CampaignInput(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    preferences: Preferences
class ContactInput(BaseModel):
    opportunity_id: str
    email: EmailStr
    source_url: HttpUrl
    role: str = Field(default='Recruiting', max_length=150)
class DraftInput(BaseModel):
    opportunity_id: str
    contact_id: str
    resume_id: str | None = None
class DraftEdit(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=40, max_length=5000)
class ApprovalInput(BaseModel):
    draft_ids: list[str] = Field(min_length=1, max_length=1000)
    mailbox_id: str
    confirmation: Literal['I authorize these recipients, messages, attachments and campaign limits']
class ApplicationInput(BaseModel):
    status: Literal['shortlisted','portal_submitted','interview','rejected','offer','withdrawn']
    notes: str = Field(default='', max_length=5000)
    interview_at: str | None = None
class ScheduleInput(BaseModel):
    interval_hours: int = Field(default=24, ge=24, le=168)
    expires_at: date
    enabled: bool = True

class FollowUpApproval(BaseModel):
    mailbox_id: str
    body: str = Field(min_length=40,max_length=1500)
    confirmation: Literal['I authorize this one follow-up to the original recipient']
