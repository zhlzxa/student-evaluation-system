import type { Meta, StoryObj } from '@storybook/react';
import { ReactQueryProvider } from '../../components/providers/react-query';
import { useQuery } from '@tanstack/react-query';

const meta: Meta<typeof ReactQueryProvider> = {
  title: 'Providers/ReactQueryProvider',
  component: ReactQueryProvider,
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof meta>;

// Sample component that uses React Query
const TestComponent = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['test'],
    queryFn: async () => {
      await new Promise(resolve => setTimeout(resolve, 1000));
      return { message: 'Hello from React Query!', count: 42 };
    },
  });

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error occurred</div>;

  return (
    <div style={{ padding: '20px' }}>
      <h3>React Query Test Component</h3>
      <p>Message: {data?.message}</p>
      <p>Count: {data?.count}</p>
    </div>
  );
};

export const Default: Story = {
  args: {
    children: <TestComponent />,
  },
};

const MultipleQueriesComponent = () => {
  const query1 = useQuery({
    queryKey: ['users'],
    queryFn: async () => {
      await new Promise(resolve => setTimeout(resolve, 800));
      return [
        { id: 1, name: 'John Doe' },
        { id: 2, name: 'Jane Smith' },
      ];
    },
  });

  const query2 = useQuery({
    queryKey: ['posts'],
    queryFn: async () => {
      await new Promise(resolve => setTimeout(resolve, 1200));
      return [
        { id: 1, title: 'First Post' },
        { id: 2, title: 'Second Post' },
      ];
    },
  });

  return (
    <div style={{ padding: '20px' }}>
      <h3>Multiple Queries Example</h3>
      
      <div style={{ marginBottom: '20px' }}>
        <h4>Users {query1.isLoading && '(loading...)'}:</h4>
        {query1.data?.map(user => (
          <p key={user.id}>{user.name}</p>
        ))}
      </div>

      <div>
        <h4>Posts {query2.isLoading && '(loading...)'}:</h4>
        {query2.data?.map(post => (
          <p key={post.id}>{post.title}</p>
        ))}
      </div>
    </div>
  );
};

export const WithMultipleQueries: Story = {
  args: {
    children: <MultipleQueriesComponent />,
  },
};