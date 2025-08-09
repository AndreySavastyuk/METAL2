/**
 * Контекст аутентификации для MetalQMS
 */
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

// Типы пользователей согласно памяти системы
export type UserRole = 'admin' | 'warehouse' | 'qc' | 'lab';

export interface User {
  id: string;
  role: UserRole;
  name: string;
  permissions: string[];
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (role: UserRole) => Promise<void>;
  logout: () => void;
  hasPermission: (permission: string) => boolean;
  hasRole: (role: UserRole) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Разрешения по ролям
const ROLE_PERMISSIONS: Record<UserRole, string[]> = {
  admin: ['*'], // Все разрешения
  warehouse: [
    'materials.view',
    'materials.create', 
    'materials.edit',
    'certificates.view',
    'certificates.upload'
  ],
  qc: [
    'materials.view',
    'inspections.view',
    'inspections.create',
    'inspections.edit',
    'certificates.view',
    'test_results.view'
  ],
  lab: [
    'materials.view',
    'tests.view',
    'tests.create',
    'tests.edit',
    'test_results.create',
    'test_results.edit',
    'certificates.view'
  ]
};

// Имена ролей для отображения
const ROLE_NAMES: Record<UserRole, string> = {
  admin: 'Администратор',
  warehouse: 'Склад',
  qc: 'ОТК (Контроль качества)',
  lab: 'ЦЗЛ (Лаборатория)'
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Проверяем сохраненную сессию при загрузке
  useEffect(() => {
    const savedRole = localStorage.getItem('metalqms_user_role') as UserRole;
    if (savedRole && ROLE_PERMISSIONS[savedRole]) {
      const userData: User = {
        id: `user_${savedRole}`,
        role: savedRole,
        name: ROLE_NAMES[savedRole],
        permissions: ROLE_PERMISSIONS[savedRole]
      };
      setUser(userData);
    }
    setIsLoading(false);
  }, []);

  const login = async (role: UserRole): Promise<void> => {
    try {
      setIsLoading(true);
      
      // Имитация API вызова
      await new Promise(resolve => setTimeout(resolve, 500));
      
      const userData: User = {
        id: `user_${role}`,
        role,
        name: ROLE_NAMES[role],
        permissions: ROLE_PERMISSIONS[role]
      };
      
      setUser(userData);
      localStorage.setItem('metalqms_user_role', role);
      
      console.log(`✅ Пользователь вошел как: ${ROLE_NAMES[role]}`);
    } catch (error) {
      console.error('Ошибка входа:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = (): void => {
    setUser(null);
    localStorage.removeItem('metalqms_user_role');
    console.log('👋 Пользователь вышел из системы');
  };

  const hasPermission = (permission: string): boolean => {
    if (!user) return false;
    return user.permissions.includes('*') || user.permissions.includes(permission);
  };

  const hasRole = (role: UserRole): boolean => {
    return user?.role === role;
  };

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    logout,
    hasPermission,
    hasRole
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;