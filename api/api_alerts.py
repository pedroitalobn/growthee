from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from .database import get_db
from .models import APIRequestLog, APIAlertConfig
import logging
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import os

logger = logging.getLogger(__name__)

class APIAlertManager:
    def __init__(self):
        self.alert_configs = {
            'brave_browser': {'hourly_limit': 100, 'daily_limit': 1000, 'cost_limit': 50.0},
            'firecrawl': {'hourly_limit': 50, 'daily_limit': 500, 'cost_limit': 25.0},
            'deepseek': {'hourly_limit': 200, 'daily_limit': 2000, 'cost_limit': 100.0},
            'chatgpt': {'hourly_limit': 150, 'daily_limit': 1500, 'cost_limit': 75.0},
            'claude': {'hourly_limit': 150, 'daily_limit': 1500, 'cost_limit': 75.0},
            'default': {'hourly_limit': 100, 'daily_limit': 1000, 'cost_limit': 50.0}
        }
    
    def check_usage_limits(self, db: Session, service: str) -> Dict:
        """Verifica se o uso de uma API está dentro dos limites"""
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        
        # Buscar configuração do serviço
        config = self.alert_configs.get(service, self.alert_configs['default'])
        
        # Contar requests na última hora
        hourly_count = db.query(func.count(APIRequestLog.id)).filter(
            and_(
                APIRequestLog.service == service,
                APIRequestLog.timestamp >= hour_ago
            )
        ).scalar() or 0
        
        # Contar requests no último dia
        daily_count = db.query(func.count(APIRequestLog.id)).filter(
            and_(
                APIRequestLog.service == service,
                APIRequestLog.timestamp >= day_ago
            )
        ).scalar() or 0
        
        # Calcular custo no último dia
        daily_cost = db.query(func.sum(APIRequestLog.cost)).filter(
            and_(
                APIRequestLog.service == service,
                APIRequestLog.timestamp >= day_ago
            )
        ).scalar() or 0.0
        
        # Verificar limites
        alerts = []
        
        if hourly_count >= config['hourly_limit']:
            alerts.append({
                'type': 'hourly_limit',
                'service': service,
                'current': hourly_count,
                'limit': config['hourly_limit'],
                'severity': 'high' if hourly_count >= config['hourly_limit'] * 1.2 else 'medium'
            })
        
        if daily_count >= config['daily_limit']:
            alerts.append({
                'type': 'daily_limit',
                'service': service,
                'current': daily_count,
                'limit': config['daily_limit'],
                'severity': 'high' if daily_count >= config['daily_limit'] * 1.2 else 'medium'
            })
        
        if daily_cost >= config['cost_limit']:
            alerts.append({
                'type': 'cost_limit',
                'service': service,
                'current': daily_cost,
                'limit': config['cost_limit'],
                'severity': 'high' if daily_cost >= config['cost_limit'] * 1.2 else 'medium'
            })
        
        return {
            'service': service,
            'hourly_usage': hourly_count,
            'daily_usage': daily_count,
            'daily_cost': daily_cost,
            'alerts': alerts,
            'limits': config
        }
    
    def check_all_services(self, db: Session) -> List[Dict]:
        """Verifica limites para todos os serviços"""
        services = db.query(APIRequestLog.service).distinct().all()
        results = []
        
        for (service,) in services:
            result = self.check_usage_limits(db, service)
            if result['alerts']:
                results.append(result)
        
        return results
    
    async def send_alert_email(self, alert_data: Dict):
        """Envia email de alerta"""
        try:
            smtp_server = os.getenv('SMTP_SERVER', 'localhost')
            smtp_port = int(os.getenv('SMTP_PORT', '587'))
            smtp_user = os.getenv('SMTP_USER')
            smtp_password = os.getenv('SMTP_PASSWORD')
            alert_email = os.getenv('ALERT_EMAIL', 'admin@growthee.com')
            
            if not smtp_user or not smtp_password:
                logger.warning("SMTP credentials not configured, skipping email alert")
                return
            
            msg = MIMEMultipart()
            msg['From'] = smtp_user
            msg['To'] = alert_email
            msg['Subject'] = f"API Usage Alert - {alert_data['service']}"
            
            body = f"""
            Alerta de Uso de API - {alert_data['service']}
            
            Detalhes:
            - Serviço: {alert_data['service']}
            - Uso por hora: {alert_data['hourly_usage']}
            - Uso diário: {alert_data['daily_usage']}
            - Custo diário: ${alert_data['daily_cost']:.2f}
            
            Alertas:
            """
            
            for alert in alert_data['alerts']:
                body += f"""
            - {alert['type']}: {alert['current']} / {alert['limit']} (Severidade: {alert['severity']})
                """
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Alert email sent for service {alert_data['service']}")
            
        except Exception as e:
            logger.error(f"Failed to send alert email: {e}")
    
    async def process_alerts(self):
        """Processa alertas de forma assíncrona"""
        db = next(get_db())
        try:
            alert_results = self.check_all_services(db)
            
            for result in alert_results:
                await self.send_alert_email(result)
                
                # Log do alerta
                logger.warning(
                    f"API usage alert for {result['service']}: "
                    f"{len(result['alerts'])} alerts triggered"
                )
        
        except Exception as e:
            logger.error(f"Error processing alerts: {e}")
        finally:
            db.close()
    
    def get_alert_summary(self, db: Session) -> Dict:
        """Retorna resumo de alertas para o dashboard"""
        services = db.query(APIRequestLog.service).distinct().all()
        summary = {
            'total_services': len(services),
            'services_with_alerts': 0,
            'high_severity_alerts': 0,
            'medium_severity_alerts': 0,
            'services_status': []
        }
        
        for (service,) in services:
            result = self.check_usage_limits(db, service)
            
            service_status = {
                'service': service,
                'status': 'ok',
                'alert_count': len(result['alerts']),
                'usage_percentage': {
                    'hourly': (result['hourly_usage'] / result['limits']['hourly_limit']) * 100,
                    'daily': (result['daily_usage'] / result['limits']['daily_limit']) * 100,
                    'cost': (result['daily_cost'] / result['limits']['cost_limit']) * 100
                }
            }
            
            if result['alerts']:
                summary['services_with_alerts'] += 1
                service_status['status'] = 'alert'
                
                for alert in result['alerts']:
                    if alert['severity'] == 'high':
                        summary['high_severity_alerts'] += 1
                        service_status['status'] = 'critical'
                    elif alert['severity'] == 'medium':
                        summary['medium_severity_alerts'] += 1
            
            summary['services_status'].append(service_status)
        
        return summary

# Instância global do gerenciador de alertas
alert_manager = APIAlertManager()

# Função para executar verificação periódica
async def run_periodic_alerts():
    """Executa verificação de alertas a cada hora"""
    while True:
        try:
            await alert_manager.process_alerts()
            await asyncio.sleep(3600)  # 1 hora
        except Exception as e:
            logger.error(f"Error in periodic alerts: {e}")
            await asyncio.sleep(300)  # 5 minutos em caso de erro