/**
 * Компонент breadcrumb навигации
 */
import React from 'react';
import { Breadcrumbs as MuiBreadcrumbs, Link, Typography, Box } from '@mui/material';
import { NavigateNext, Home } from '@mui/icons-material';
import { useLocation, Link as RouterLink } from 'react-router-dom';

interface BreadcrumbItem {
  label: string;
  path?: string;
  icon?: React.ReactNode;
}

const Breadcrumbs: React.FC = () => {
  const location = useLocation();
  
  // Генерируем breadcrumbs на основе текущего пути
  const generateBreadcrumbs = (): BreadcrumbItem[] => {
    const pathSegments = location.pathname.split('/').filter(Boolean);
    const breadcrumbs: BreadcrumbItem[] = [
      {
        label: 'Главная',
        path: '/',
        icon: <Home sx={{ mr: 0.5 }} fontSize="inherit" />
      }
    ];

    let currentPath = '';
    
    pathSegments.forEach((segment, index) => {
      currentPath += `/${segment}`;
      
      // Определяем название сегмента
      let label = segment;
      switch (segment) {
        case 'materials':
          label = 'Материалы';
          break;
        case 'new':
          label = 'Новый материал';
          break;
        case 'edit':
          label = 'Редактирование';
          break;
        case 'qc':
          label = 'Контроль качества';
          break;
        case 'inspections':
          label = 'Инспекции';
          break;
        case 'lab':
          label = 'Лаборатория';
          break;
        case 'tests':
          label = 'Тесты';
          break;
        case 'production':
          label = 'Производство';
          break;
        default:
          // Если это ID (число), показываем как "Материал №ID"
          if (/^\d+$/.test(segment)) {
            label = `Материал №${segment}`;
          }
      }

      breadcrumbs.push({
        label,
        path: index === pathSegments.length - 1 ? undefined : currentPath
      });
    });

    return breadcrumbs;
  };

  const breadcrumbs = generateBreadcrumbs();

  // Не показываем breadcrumbs на главной странице
  if (location.pathname === '/') {
    return null;
  }

  return (
    <Box sx={{ mb: 2 }}>
      <MuiBreadcrumbs
        separator={<NavigateNext fontSize="small" />}
        aria-label="breadcrumb"
      >
        {breadcrumbs.map((breadcrumb, index) => {
          const isLast = index === breadcrumbs.length - 1;
          
          if (isLast || !breadcrumb.path) {
            return (
              <Typography 
                key={index}
                color="text.primary"
                sx={{ display: 'flex', alignItems: 'center' }}
              >
                {breadcrumb.icon}
                {breadcrumb.label}
              </Typography>
            );
          }
          
          return (
            <Link
              key={index}
              component={RouterLink}
              to={breadcrumb.path}
              underline="hover"
              color="inherit"
              sx={{ display: 'flex', alignItems: 'center' }}
            >
              {breadcrumb.icon}
              {breadcrumb.label}
            </Link>
          );
        })}
      </MuiBreadcrumbs>
    </Box>
  );
};

export default Breadcrumbs;