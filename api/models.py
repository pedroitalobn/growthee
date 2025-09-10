from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List, Dict, Any

class CompanyRequest(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    linkedin_url: Optional[str] = None
    instagram_url: Optional[str] = None
    region: Optional[str] = None  # ✅ Novo campo para região/estado
    country: Optional[str] = None  # ✅ Novo campo para país
    
    # Super enrichment options
    extract_social_media: Optional[bool] = True
    extract_linkedin: Optional[bool] = True
    use_brave_search: Optional[bool] = True
    deep_extraction: Optional[bool] = False

    @property
    def has_valid_input(self) -> bool:
        """Verifica se a requisição tem pelo menos um campo válido para busca"""
        # Aceita se tem domínio, URL do LinkedIn/Instagram, ou nome da empresa
        # Se tem apenas nome, deve ter pelo menos região ou país para busca efetiva
        if self.domain or self.linkedin_url or self.instagram_url:
            return True
        if self.name and (self.region or self.country):
            return True
        return bool(self.name)  # Aceita apenas nome como último recurso

class SocialMedia(BaseModel):
    platform: str
    url: str
    followers: Optional[int] = None

class InstagramData(BaseModel):
    url: Optional[str] = None
    name: Optional[str] = None
    user: Optional[str] = None
    email: Optional[str] = None  # Mantido para compatibilidade
    phone: Optional[str] = None  # Mantido para compatibilidade
    emails: Optional[List[str]] = []  # Novo campo para múltiplos emails
    phones: Optional[List[str]] = []  # Novo campo para múltiplos telefones
    whatsapps: Optional[List[str]] = []  # Novo campo para múltiplos whatsapps
    bio: Optional[str] = None
    followers: Optional[int] = None
    following: Optional[int] = None
    posts: Optional[int] = None

class LinkedInData(BaseModel):
    url: Optional[str] = None
    company_name: Optional[str] = None
    followers: Optional[int] = None
    employees_count: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    # Dados de localização
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    street_address: Optional[str] = None

class WhatsAppData(BaseModel):
    phone: Optional[str] = None
    business_name: Optional[str] = None
    verified: Optional[bool] = None

class TikTokData(BaseModel):
    url: Optional[str] = None
    username: Optional[str] = None
    followers: Optional[int] = None
    likes: Optional[int] = None
    bio: Optional[str] = None

class TelegramData(BaseModel):
    url: Optional[str] = None
    username: Optional[str] = None
    members: Optional[int] = None
    description: Optional[str] = None

class Employee(BaseModel):
    name: str
    title: str
    linkedin_url: Optional[str] = None

class CompanyResponse(BaseModel):
    # Core company information
    name: Optional[str] = None
    company_name: Optional[str] = None  # Alias for name
    description: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = None
    company_size: Optional[str] = None  # Enhanced size info
    founded: Optional[str] = None
    headquarters: Optional[str] = None
    website: Optional[str] = None
    
    # Employee information
    employee_count: Optional[str] = None
    employee_count_exact: Optional[int] = None
    employee_count_range: Optional[str] = None
    follower_count: Optional[int] = None
    
    # Location fields (enhanced)
    country: Optional[str] = None
    country_code: Optional[str] = None
    region: Optional[str] = None
    region_code: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    street_address: Optional[str] = None
    country_dial_code: Optional[str] = None
    
    # Company details
    company_history: Optional[str] = None
    specialties: Optional[List[str]] = None
    
    # Enhanced fields from website scraping
    recent_news: List[dict] = []
    contact_info: dict = {}
    team_info: dict = {}
    products_services: List[dict] = []
    company_values: List[dict] = []
    certifications: List[dict] = []
    
    employees: List[dict] = []
    
    # Enhanced social media data
    instagram: Optional[InstagramData] = None
    linkedin: Optional[LinkedInData] = None
    whatsapp: Optional[WhatsAppData] = None
    tiktok: Optional[TikTokData] = None
    telegram: Optional[TelegramData] = None
    
    # Status fields
    enrich: bool = True  # Indica se o enriquecimento foi realizado com sucesso
    error: Optional[str] = None  # Mensagem de erro, se houver

# Modelos para enriquecimento de pessoas
class PersonRequest(BaseModel):
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    phone: Optional[str] = None
    full_name: Optional[str] = None
    company_name: Optional[str] = None
    company_linkedin: Optional[str] = None
    company_website: Optional[str] = None
    domain: Optional[str] = None
    company_domain: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None

    @property
    def has_valid_input(self) -> bool:
        return bool(self.email or self.linkedin_url or self.phone or self.full_name or self.domain or self.company_domain)

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

class PersonData(BaseModel):
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
    
    # Enhanced social media data
    instagram: Optional[InstagramData] = None
    linkedin_data: Optional[LinkedInData] = None
    whatsapp: Optional[WhatsAppData] = None
    tiktok: Optional[TikTokData] = None
    telegram: Optional[TelegramData] = None
    confidence_score: Optional[float] = None
    data_source: Optional[str] = None
    last_updated: Optional[str] = None
    error: Optional[str] = None

class PersonResponse(BaseModel):
    success: bool = True
    data: Optional[Dict[str, Any]] = None
    message: str = "Person enriched successfully"
    enrich: bool = True

# API Request Tracking Models
class APIRequestLog(BaseModel):
    id: Optional[str] = None
    service_name: str  # brave_browser, firecrawl, deepseek, chatgpt, claude, etc.
    endpoint: str
    method: str = "GET"
    request_data: Optional[Dict[str, Any]] = None
    response_status: Optional[int] = None
    response_time_ms: Optional[float] = None
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None
    user_id: Optional[str] = None
    timestamp: str
    error_message: Optional[str] = None
    request_size_bytes: Optional[int] = None
    response_size_bytes: Optional[int] = None

class APIServiceStats(BaseModel):
    service_name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    avg_response_time_ms: float = 0.0
    last_request_timestamp: Optional[str] = None
    daily_requests: int = 0
    monthly_requests: int = 0

class APIUsageResponse(BaseModel):
    services: List[APIServiceStats] = []
    total_requests_today: int = 0
    total_cost_today: float = 0.0
    total_tokens_today: int = 0
    most_used_service: Optional[str] = None
    cost_breakdown: Dict[str, float] = {}
    request_trends: Dict[str, List[int]] = {}  # Last 7 days

class APIAlertConfig(BaseModel):
    service_name: str
    max_daily_requests: Optional[int] = None
    max_daily_cost: Optional[float] = None
    max_hourly_requests: Optional[int] = None
    alert_email: Optional[str] = None
    enabled: bool = True