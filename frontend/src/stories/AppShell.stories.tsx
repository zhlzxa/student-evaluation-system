import type { Meta, StoryObj } from '@storybook/react';
import { AppShell } from '../../components/layout/AppShell';

const meta: Meta<typeof AppShell> = {
  title: 'Layout/AppShell',
  component: AppShell,
  parameters: {
    layout: 'fullscreen',
  },
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    children: (
      <div style={{ padding: '20px' }}>
        <h2>Sample Content</h2>
        <p>This is sample content inside the AppShell component.</p>
        <p>The AppShell provides navigation, header, and layout structure.</p>
      </div>
    ),
  },
};

export const WithDashboard: Story = {
  args: {
    children: (
      <div style={{ padding: '20px' }}>
        <h1>Dashboard</h1>
        <div style={{ display: 'flex', gap: '20px', marginTop: '20px' }}>
          <div style={{ 
            background: '#f5f5f5', 
            padding: '20px', 
            borderRadius: '8px',
            flex: 1,
          }}>
            <h3>Quick Actions</h3>
            <button>New Assessment</button>
          </div>
          <div style={{ 
            background: '#f5f5f5', 
            padding: '20px', 
            borderRadius: '8px',
            flex: 1,
          }}>
            <h3>Recent Evaluations</h3>
            <p>Count: 5</p>
          </div>
        </div>
      </div>
    ),
  },
  parameters: {
    nextjs: {
      navigation: {
        pathname: '/',
      },
    },
  },
};

export const WithAssessments: Story = {
  args: {
    children: (
      <div style={{ padding: '20px' }}>
        <h1>Assessments</h1>
        <div style={{ marginTop: '20px' }}>
          <div style={{ 
            background: '#f5f5f5', 
            padding: '15px', 
            borderRadius: '8px',
            marginBottom: '10px',
          }}>
            <h4>Assessment Run #1</h4>
            <p>Status: Completed</p>
          </div>
          <div style={{ 
            background: '#f5f5f5', 
            padding: '15px', 
            borderRadius: '8px',
            marginBottom: '10px',
          }}>
            <h4>Assessment Run #2</h4>
            <p>Status: In Progress</p>
          </div>
        </div>
      </div>
    ),
  },
  parameters: {
    nextjs: {
      navigation: {
        pathname: '/assessments',
      },
    },
  },
};