from scrapy import Item, Field

class CompanyItem(Item):
    name = Field()
    linkedin_url = Field()
    website = Field()
    description = Field()
    industry = Field()
    size = Field()
    founded = Field()
    headquarters = Field()
    employees = Field()
    social_media = Field()

class EmployeeItem(Item):
    name = Field()
    title = Field()
    company = Field()
    linkedin_url = Field()
    location = Field()
    experience = Field()
    skills = Field()
