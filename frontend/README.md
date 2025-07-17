# Crypto News Agent Frontend

Modern React frontend for real-time crypto news Q&A, built with TypeScript, Tailwind CSS, and Vite. Features streaming responses, conversation history, and a responsive chat interface.

## Features

- **Real-time Chat Interface**: Modern, responsive chat UI
- **Streaming Responses**: Word-by-word streaming via Server-Sent Events
- **Conversation History**: Context-aware chat with message persistence
- **Source Attribution**: Display news sources for each answer
- **Stop Generation**: Cancel ongoing requests
- **Responsive Design**: Works on desktop and mobile
- **Modern UI**: Clean design with Tailwind CSS

## Tech Stack

- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **Icons**: Lucide React
- **HTTP Client**: Fetch API with SSE support
- **State Management**: React hooks (useState, useEffect)

## Installation

1. **Navigate to the frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Set up environment variables**:
   Create a `.env` file in the frontend directory:
   ```bash
   VITE_API_BASE_URL=http://localhost:8000
   ```

## Development

### Running the Frontend
```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`

### Building for Production
```bash
npm run build
```

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build

## Architecture

### Core Components

1. **ChatPage** (`src/pages/ChatPage.tsx`)
   - Main chat interface
   - Manages conversation state
   - Handles streaming responses

2. **ChatInput** (`src/components/ChatInput.tsx`)
   - Message input component
   - Form validation and submission
   - Loading states

3. **ChatMessage** (`src/components/ChatMessage.tsx`)
   - Individual message display
   - Source attribution
   - User/assistant message styling

4. **SourceList** (`src/components/SourceList.tsx`)
   - Displays news sources
   - Clickable links to articles
   - Source metadata

### API Integration

The frontend communicates with the backend via:

- **SSE Streaming**: Real-time word-by-word responses
- **REST API**: Question submission and session management
- **Error Handling**: Graceful error display and recovery

### State Management

- **Conversation State**: Messages, streaming status, sources
- **UI State**: Loading states, error messages, input validation
- **Session Management**: Session IDs for conversation continuity

## Project Structure

```
frontend/
├── src/
│   ├── components/     # Reusable UI components
│   ├── pages/         # Page components
│   ├── apis/          # API client functions
│   ├── types/         # TypeScript type definitions
│   ├── utils/         # Utility functions
│   └── styles/        # Global styles
├── public/            # Static assets
├── package.json       # Dependencies
└── README.md
```

## User Interface

### Chat Interface
- Clean, modern chat layout
- Message bubbles with user/assistant distinction
- Real-time streaming with typing indicators
- Source attribution for each answer

### Responsive Design
- Mobile-first approach
- Responsive grid layout
- Touch-friendly interface
- Optimized for various screen sizes

### Accessibility
- Keyboard navigation support
- Screen reader compatibility
- High contrast mode support
- Focus management

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_BASE_URL` | Backend API URL | `http://localhost:8000` |
