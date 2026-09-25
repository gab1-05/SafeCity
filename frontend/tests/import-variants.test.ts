// Test 1: Original alias import
import { LoginPage } from '@/pages/public/LoginPage';
console.log('Test 1 - @/pages/public/LoginPage:', LoginPage ? 'Found' : 'Undefined');

// Test 2: Relative path import
import { LoginPage as LoginPage2 } from '../src/pages/public/LoginPage';
console.log('Test 2 - relative path:', LoginPage2 ? 'Found' : 'Undefined');

// Test 3: Alias with different casing
import { LoginPage as LoginPage3 } from '@/Pages/public/LoginPage';
console.log('Test 3 - @/Pages/public/LoginPage:', LoginPage3 ? 'Found' : 'Undefined');

// Test 4: Alias missing public
import { LoginPage as LoginPage4 } from '@/pages/LoginPage';
console.log('Test 4 - @/pages/LoginPage:', LoginPage4 ? 'Found' : 'Undefined');

export {};
