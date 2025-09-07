import type { Meta, StoryObj } from '@storybook/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Home from '../../app/page';

// Mock the useRouter hook
const mockRouter = {
  push: fn(),
  replace: fn(),
  prefetch: fn(),
  back: fn(),
  forward: fn(),
  refresh: fn(),
};

// Mock the API hook
const mockApi = fn().mockResolvedValue({
  ok: true,
  json: () => Promise.resolve([
    { id: 1, name: 'Sample Run 1', status: 'completed' },
    { id: 2, name: 'Sample Run 2', status: 'pending' },
  ]),
});

const meta: Meta<typeof Home> = {
  title: 'Pages/HomePage',
  component: Home,
  parameters: {
    layout: 'padded',
    msw: {
      handlers: [
        // Mock API endpoint for assessment runs
        {
          method: 'get',
          url: '/assessments/runs',
          response: [
            { id: 1, name: 'Sample Run 1', status: 'completed' },
            { id: 2, name: 'Sample Run 2', status: 'pending' },
          ],
        },
      ],
    },
    nextjs: {
      navigation: {
        pathname: '/',
      },
    },
  },
  decorators: [
    (Story) => {
      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false },
        },
      });

      return (
        <QueryClientProvider client={queryClient}>
          <Story />
        </QueryClientProvider>
      );
    },
  ],
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const WithManyRuns: Story = {
  parameters: {
    msw: {
      handlers: [
        {
          method: 'get',
          url: '/assessments/runs',
          response: Array.from({ length: 15 }, (_, i) => ({
            id: i + 1,
            name: `Assessment Run ${i + 1}`,
            status: i % 3 === 0 ? 'completed' : i % 3 === 1 ? 'pending' : 'failed',
          })),
        },
      ],
    },
  },
};

export const WithNoRuns: Story = {
  parameters: {
    msw: {
      handlers: [
        {
          method: 'get',
          url: '/assessments/runs',
          response: [],
        },
      ],
    },
  },
};

export const WithAPIError: Story = {
  parameters: {
    msw: {
      handlers: [
        {
          method: 'get',
          url: '/assessments/runs',
          status: 500,
          response: { error: 'Internal Server Error' },
        },
      ],
    },
  },
};