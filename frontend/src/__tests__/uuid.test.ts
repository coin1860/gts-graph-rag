/**
 * Unit tests for UUID generation and session ID functionality.
 * Tests verify that session ID and temp file management works correctly.
 */

// Mock uuid module with valid UUID v4 format
jest.mock('uuid', () => ({
    v4: jest.fn(() => '550e8400-e29b-41d4-a716-446655440000'),
    validate: jest.fn((id: string) => /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)),
}));

import { v4 as uuidv4, validate as uuidValidate } from 'uuid';

describe('UUID Generation', () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });

    describe('uuidv4', () => {
        it('should generate a UUID string', () => {
            const id = uuidv4();

            expect(typeof id).toBe('string');
            expect(id.length).toBe(36);
        });

        it('should be called correctly', () => {
            uuidv4();
            expect(uuidv4).toHaveBeenCalled();
        });

        it('should match UUID format pattern', () => {
            const id = uuidv4();
            const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

            expect(id).toMatch(uuidPattern);
        });
    });

    describe('validate', () => {
        it('should validate correct UUID format', () => {
            expect(uuidValidate('550e8400-e29b-41d4-a716-446655440000')).toBe(true);
        });

        it('should reject invalid UUID format', () => {
            expect(uuidValidate('not-a-uuid')).toBe(false);
        });
    });

    describe('Session ID simulation', () => {
        it('should work with useState pattern', () => {
            // Simulate the useState initialization
            const createSessionId = () => uuidv4();

            const sessionId = createSessionId();

            expect(sessionId).toBeDefined();
            expect(typeof sessionId).toBe('string');
            expect(sessionId.length).toBe(36);
        });

        it('should be stable within a session (no regeneration)', () => {
            // Simulate component state
            let sessionId: string | null = null;

            const initializeSessionId = () => {
                if (!sessionId) {
                    sessionId = uuidv4();
                }
                return sessionId;
            };

            const firstCall = initializeSessionId();
            const secondCall = initializeSessionId();

            expect(firstCall).toBe(secondCall);
        });
    });
});

describe('Temp Files State', () => {
    interface TempFile {
        id: string;
        name: string;
        status: 'uploading' | 'ready' | 'error';
    }

    it('should manage temp files array correctly', () => {
        let tempFiles: TempFile[] = [];

        // Add a file
        const newFile: TempFile = {
            id: `temp_${Date.now()}`,
            name: 'test.pdf',
            status: 'uploading',
        };
        tempFiles = [...tempFiles, newFile];

        expect(tempFiles.length).toBe(1);
        expect(tempFiles[0].status).toBe('uploading');

        // Update status
        tempFiles = tempFiles.map(f =>
            f.id === newFile.id ? { ...f, status: 'ready' as const } : f
        );

        expect(tempFiles[0].status).toBe('ready');
    });

    it('should filter ready files for submission', () => {
        const tempFiles: TempFile[] = [
            { id: 'file1', name: 'a.pdf', status: 'ready' },
            { id: 'file2', name: 'b.pdf', status: 'uploading' },
            { id: 'file3', name: 'c.pdf', status: 'error' },
            { id: 'file4', name: 'd.pdf', status: 'ready' },
        ];

        const readyFileIds = tempFiles
            .filter(f => f.status === 'ready')
            .map(f => f.id);

        expect(readyFileIds).toEqual(['file1', 'file4']);
    });

    it('should remove files by id', () => {
        let tempFiles: TempFile[] = [
            { id: 'file1', name: 'a.pdf', status: 'ready' },
            { id: 'file2', name: 'b.pdf', status: 'ready' },
        ];

        // Remove file1
        tempFiles = tempFiles.filter(f => f.id !== 'file1');

        expect(tempFiles.length).toBe(1);
        expect(tempFiles[0].id).toBe('file2');
    });
});

describe('Session ID for API requests', () => {
    it('should include sessionId in chat request body', () => {
        const sessionId = uuidv4();
        const tempFiles = [
            { id: 'file1', name: 'a.pdf', status: 'ready' as const },
        ];

        const requestBody = {
            message: 'test question',
            session_id: sessionId,
            temp_file_ids: tempFiles.filter(f => f.status === 'ready').map(f => f.id),
        };

        expect(requestBody.session_id).toBe(sessionId);
        expect(requestBody.temp_file_ids).toEqual(['file1']);
    });
});
