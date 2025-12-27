import '@testing-library/jest-dom';

// Mock next/navigation
jest.mock('next/navigation', () => ({
    useRouter: () => ({
        push: jest.fn(),
        replace: jest.fn(),
        prefetch: jest.fn(),
    }),
    useSearchParams: () => new URLSearchParams(),
    usePathname: () => '',
}));

// Mock next/dynamic
jest.mock('next/dynamic', () => () => {
    const DynamicComponent = () => null;
    DynamicComponent.displayName = 'DynamicComponent';
    return DynamicComponent;
});

// Mock localStorage
const localStorageMock = {
    getItem: jest.fn(),
    setItem: jest.fn(),
    removeItem: jest.fn(),
    clear: jest.fn(),
};
Object.defineProperty(window, 'localStorage', { value: localStorageMock });
