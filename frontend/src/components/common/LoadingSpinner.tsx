/**
 * Компонент для отображения состояния загрузки
 */
import React from 'react';
import {
  Box,
  CircularProgress,
  Typography,
  Skeleton,
  Card,
  CardContent,
  LinearProgress,
} from '@mui/material';

interface LoadingSpinnerProps {
  size?: number;
  message?: string;
  variant?: 'circular' | 'linear' | 'skeleton';
  fullScreen?: boolean;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 40,
  message = 'Загрузка...',
  variant = 'circular',
  fullScreen = false,
}) => {
  const content = (() => {
    switch (variant) {
      case 'linear':
        return (
          <Box width="100%">
            {message && (
              <Typography variant="body2" color="text.secondary" mb={1}>
                {message}
              </Typography>
            )}
            <LinearProgress />
          </Box>
        );
      
      case 'skeleton':
        return (
          <Box>
            <Skeleton variant="text" height={40} />
            <Skeleton variant="text" height={30} />
            <Skeleton variant="text" height={30} width="60%" />
            <Skeleton variant="rectangular" height={200} sx={{ mt: 2 }} />
          </Box>
        );
      
      default:
        return (
          <Box display="flex" flexDirection="column" alignItems="center" gap={2}>
            <CircularProgress size={size} />
            {message && (
              <Typography variant="body2" color="text.secondary">
                {message}
              </Typography>
            )}
          </Box>
        );
    }
  })();

  if (fullScreen) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="100vh"
        bgcolor="background.default"
      >
        {content}
      </Box>
    );
  }

  return (
    <Box
      display="flex"
      justifyContent="center"
      alignItems="center"
      p={3}
    >
      {content}
    </Box>
  );
};

interface TableLoadingProps {
  rows?: number;
  columns?: number;
}

export const TableLoading: React.FC<TableLoadingProps> = ({
  rows = 5,
  columns = 6,
}) => (
  <Box>
    {[...Array(rows)].map((_, rowIndex) => (
      <Box key={rowIndex} display="flex" gap={2} mb={1}>
        {[...Array(columns)].map((_, colIndex) => (
          <Skeleton
            key={colIndex}
            variant="text"
            height={48}
            sx={{ flex: 1 }}
          />
        ))}
      </Box>
    ))}
  </Box>
);

interface CardLoadingProps {
  count?: number;
}

export const CardLoading: React.FC<CardLoadingProps> = ({ count = 3 }) => (
  <Box>
    {[...Array(count)].map((_, index) => (
      <Card key={index} sx={{ mb: 2 }}>
        <CardContent>
          <Skeleton variant="text" height={32} width="40%" />
          <Skeleton variant="text" height={24} sx={{ mt: 1 }} />
          <Skeleton variant="text" height={24} width="80%" />
          <Skeleton variant="rectangular" height={120} sx={{ mt: 2 }} />
        </CardContent>
      </Card>
    ))}
  </Box>
);

export default LoadingSpinner;