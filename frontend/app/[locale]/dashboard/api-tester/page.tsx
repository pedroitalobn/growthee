import { useTranslations } from 'next-intl';
import { ApiTester } from '@/components/dashboard/api-tester';

export default function ApiTesterPage() {
  const t = useTranslations('apiTester');
  
  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">{t('title')}</h1>
      <ApiTester />
    </div>
  );
}