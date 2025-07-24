from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List

class CompanyRequest(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    linkedin_url: Optional[str] = None
    region: Optional[str] = None  # ✅ Novo campo para região/estado
    country: Optional[str] = None  # ✅ Novo campo para país

    @property
    def has_valid_input(self) -> bool:
        return bool(self.name or self.domain or self.linkedin_url)

class SocialMedia(BaseModel):
    platform: str
    url: str
    followers: Optional[int] = None

class Employee(BaseModel):
    name: str
    title: str
    linkedin_url: Optional[str] = None

class CompanyResponse(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = None
    founded: Optional[str] = None
    headquarters: Optional[str] = None
    website: Optional[str] = None
    linkedin: Optional[str] = None
    
    # Location fields
    country: Optional[str] = None
    country_code: Optional[str] = None
    region: Optional[str] = None
    region_code: Optional[str] = None
    city: Optional[str] = None
    country_dial_code: Optional[str] = None
    
    # Enhanced fields from website scraping
    company_history: Optional[str] = None
    recent_news: List[dict] = []
    contact_info: dict = {}
    team_info: dict = {}
    products_services: List[dict] = []
    company_values: List[dict] = []
    certifications: List[dict] = []
    
    employees: List[dict] = []
    social_media: List[dict] = []
    error: Optional[str] = None

# Modelos para enriquecimento de pessoas
class PersonRequest(BaseModel):
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    phone: Optional[str] = None
    full_name: Optional[str] = None
    company_name: Optional[str] = None
    company_linkedin: Optional[str] = None
    company_website: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None

    @property
    def has_valid_input(self) -> bool:
        return bool(self.email or self.linkedin_url or self.phone or self.full_name)

class PersonExperience(BaseModel):
    company: str
    title: str
    duration: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None

class PersonEducation(BaseModel):
    institution: str
    degree: Optional[str] = None
    field: Optional[str] = None
    duration: Optional[str] = None

class PersonResponse(BaseModel):
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    email_verified: Optional[bool] = None
    phone: Optional[str] = None
    phone_verified: Optional[bool] = None
    linkedin_url: Optional[str] = None
    headline: Optional[str] = None
    current_company: Optional[str] = None
    current_title: Optional[str] = None
    location: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    profile_image: Optional[str] = None
    connections: Optional[str] = None
    skills: List[str] = []
    experience: List[PersonExperience] = []
    education: List[PersonEducation] = []
    social_media: List[dict] = []
    confidence_score: Optional[float] = None
    data_source: Optional[str] = None
    last_updated: Optional[str] = None
    error: Optional[str] = None