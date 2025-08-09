/**
 * Страница лаборатории (ЦЗЛ)
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
import { Science, Construction } from '@mui/icons-material';

const LaboratoryPage: React.FC = () => {
  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Лаборатория (ЦЗЛ)
      </Typography>
      
      <Alert severity="info" sx={{ mb: 3 }}>
        Модуль лаборатории находится в разработке
      </Alert>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <Science sx={{ mr: 2, fontSize: 40, color: 'primary.main' }} />
                <Typography variant="h6">
                  Лабораторные испытания
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary" paragraph>
                Управление тестами, анализами и испытаниями материалов
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
                <Construction sx={{ mr: 2, fontSize: 40, color: 'secondary.main' }} />
                <Typography variant="h6">
                  Оборудование
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary" paragraph>
                Калибровка и обслуживание лабораторного оборудования
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

export default LaboratoryPage;