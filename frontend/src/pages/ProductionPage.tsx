/**
 * Страница производства
 */
import React from 'react';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  Button,
  Alert
} from '@mui/material';
import { Factory, Assignment } from '@mui/icons-material';

const ProductionPage: React.FC = () => {
  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Производство
      </Typography>
      
      <Alert severity="info" sx={{ mb: 3 }}>
        Модуль производства находится в разработке
      </Alert>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <Factory sx={{ mr: 2, fontSize: 40, color: 'primary.main' }} />
                <Typography variant="h6">
                  Производственные заказы
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary" paragraph>
                Управление заказами на производство из проверенных материалов
              </Typography>
              <Button variant="outlined" disabled>
                В разработке
              </Button>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <Assignment sx={{ mr: 2, fontSize: 40, color: 'secondary.main' }} />
                <Typography variant="h6">
                  Учет материалов
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary" paragraph>
                Расход материалов в производственном процессе
              </Typography>
              <Button variant="outlined" disabled>
                В разработке
              </Button>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default ProductionPage;