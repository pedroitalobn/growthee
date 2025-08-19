def _merge_website_data(self, linkedin_data: Dict[str, Any], website_data: Dict[str, Any]) -> Dict[str, Any]:
    """Mescla dados do LinkedIn com dados do site"""
    if not website_data:
        return linkedin_data
        
    # Combinar redes sociais
    linkedin_social = linkedin_data.get('social_media', [])
    website_social = website_data.get('social_media_extended', [])
    
    all_social = linkedin_social.copy()
    for social in website_social:
        if not any(s.get('url') == social.get('url') for s in all_social):
            all_social.append(social)
    
    # Mesclar dados
    linkedin_data.update({
        'social_media': all_social,
        'company_history': website_data.get('company_history') or linkedin_data.get('company_history'),
        'recent_news': website_data.get('news_and_updates', []),  # Mantém compatibilidade
        'news_and_updates': website_data.get('news_and_updates', []),  # Novo campo
        'contact_info': website_data.get('contact_info', {}),
        'team_info': website_data.get('team_info', {'leadership': [], 'team_size_estimate': None}),
        'products_services': website_data.get('products_services', []),
        'company_values': website_data.get('company_values', []),
        'certifications': website_data.get('certifications', [])
    })
    
    return linkedin_data
