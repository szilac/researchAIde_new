import { expect } from 'vitest';
import matchers from '@testing-library/jest-dom/matchers';

// Extend Vitest's expect method with methods from react-testing-library
expect.extend(matchers);

// You can add other global setup code here if needed, for example:
// afterEach(() => {
//   cleanup(); // if you were using @testing-library/react's cleanup
// }); 