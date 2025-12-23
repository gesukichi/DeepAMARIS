import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom'
import { ChatHistoryLoadingState } from '../../api/models'

// Mock dependencies first
jest.mock('../../utils/resizeImage', () => ({
  resizeImage: jest.fn().mockResolvedValue('mock-base64-image')
}))

// Mock SVG imports
jest.mock('../../assets/Send.svg', () => 'mock-send-svg')

// Create complete mock state that matches AppState interface
const mockContextValue = {
  state: {
    isChatHistoryOpen: false,
    chatHistoryLoadingState: ChatHistoryLoadingState.Loading,
    isCosmosDBAvailable: {
      cosmosDB: true,
      status: 'Working'
    },
    chatHistory: null,
    filteredChatHistory: null,
    currentChat: null,
    frontendSettings: {
      oyd_enabled: false
    },
    feedbackState: {},
    isLoading: false,
    answerExecResult: {}
  },
  dispatch: jest.fn()
}

// Use a module factory that creates a real context
jest.mock('../../state/AppProvider', () => {
  const actualReact = jest.requireActual('react')
  return {
    AppStateContext: actualReact.createContext(mockContextValue)
  }
})

import { QuestionInput } from './QuestionInput'
import { AppStateContext } from '../../state/AppProvider'

// Proper provider wrapper using the real context
const MockAppProvider = ({ children }: { children: React.ReactNode }) => (
  <AppStateContext.Provider value={mockContextValue as any}>
    {children}
  </AppStateContext.Provider>
)

describe('QuestionInput - Mode Switch Integration (TDD)', () => {
  const defaultProps = {
    onSend: jest.fn(),
    disabled: false,
    placeholder: 'Type a question...',
    clearOnSend: true,
    conversationId: 'test-conversation-id',
    disableImageUpload: true  // デフォルトで画像アップロードを無効化してエラーを防ぐ
  }

  // Helper function to render with context
  const renderWithContext = (ui: React.ReactElement) => {
    return render(
      <MockAppProvider>
        {ui}
      </MockAppProvider>
    )
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('Red Phase: Mode Switch Display', () => {
    test('displays mode switch below send button', () => {
      const onModeChange = jest.fn()
      
      renderWithContext(
        <QuestionInput
          {...defaultProps}
          useModernRag={false}
          onModeChange={onModeChange}
        />
      )

      // Check mode switch exists using testid since Japanese text might be complex
      const modeSwitch = screen.getByTestId('mode-toggle')
      expect(modeSwitch).toBeInTheDocument()

      // Check positioning relative to send button
      const sendButton = screen.getByRole('button', { 
        name: /Ask question button/ 
      })
      const modeSwitchContainer = screen.getByTestId('mode-switch-container')
      
      expect(sendButton).toBeInTheDocument()
      expect(modeSwitchContainer).toBeInTheDocument()
    })

    test('shows correct label and tooltip for Chat mode', async () => {
      const user1 = userEvent.setup()
      
      renderWithContext(
        <QuestionInput
          {...defaultProps}
          useModernRag={false}
          onModeChange={jest.fn()}
        />
      )

      const modeSwitch = screen.getByTestId('mode-toggle')
      
      // Check Chat mode label
      expect(modeSwitch).not.toBeChecked()
      
      // Check tooltip display - use getAllByText and filter for visible element
      await user1.hover(modeSwitch)
      
      await waitFor(() => {
        const tooltipElements = screen.getAllByText(/Chatモード: Azure OpenAI による標準的な会話/)
        const visibleTooltip = tooltipElements.find(element => !element.hidden)
        expect(visibleTooltip).toBeInTheDocument()
      })
    })

    test('shows correct label and tooltip for Web Search mode', async () => {
      const user2 = userEvent.setup()
      
      renderWithContext(
        <QuestionInput
          {...defaultProps}
          useModernRag={true}
          onModeChange={jest.fn()}
        />
      )

      const modeSwitch = screen.getByTestId('mode-toggle')
      
      // Check Web Search mode label
      expect(modeSwitch).toBeChecked()
      
      // Check tooltip display - use getAllByText and filter for visible element
      await user2.hover(modeSwitch)
      
      await waitFor(() => {
        const tooltipElements = screen.getAllByText(/ドキュメント検索とWeb検索を組み合わせた高度な情報取得/)
        const visibleTooltip = tooltipElements.find(element => !element.hidden)
        expect(visibleTooltip).toBeInTheDocument()
      })
    })
  })

  describe('Red Phase: Mode Switch Functionality', () => {
    test('calls onModeChange when mode switch is clicked', async () => {
      const user3 = userEvent.setup()
      const onModeChange = jest.fn()
      
      renderWithContext(
        <QuestionInput
          {...defaultProps}
          useModernRag={false}
          onModeChange={onModeChange}
        />
      )

      const modeSwitch = screen.getByTestId('mode-toggle')
      
      await user3.click(modeSwitch)
      
      expect(onModeChange).toHaveBeenCalledWith(true)
    })

    test('supports keyboard navigation for mode switching', async () => {
      const user4 = userEvent.setup()
      const onModeChange = jest.fn()
      
      renderWithContext(
        <QuestionInput
          {...defaultProps}
          useModernRag={false}
          onModeChange={onModeChange}
        />
      )

      const modeSwitch = screen.getByTestId('mode-toggle')
      
      // Focus and use space key to toggle
      modeSwitch.focus()
      await user4.keyboard(' ')
      
      expect(onModeChange).toHaveBeenCalledWith(true)
    })
  })

  describe('Red Phase: Conditional Rendering', () => {
    test('hides mode switch when onModeChange is not provided', () => {
      renderWithContext(
        <QuestionInput
          {...defaultProps}
          useModernRag={false}
          // onModeChange not provided
        />
      )

      expect(screen.queryByTestId('mode-toggle')).not.toBeInTheDocument()
    })

    test('preserves existing functionality after adding mode switch', async () => {
      const user5 = userEvent.setup()
      const onSend = jest.fn()
      
      renderWithContext(
        <QuestionInput
          {...defaultProps}
          onSend={onSend}
          useModernRag={false}
          onModeChange={jest.fn()}
        />
      )

      const textInput = screen.getByRole('textbox')
      const sendButton = screen.getByRole('button', { 
        name: /Ask question button/ 
      })

      // Type text
      await user5.type(textInput, 'Test message')
      
      // Click send button
      await user5.click(sendButton)
      
      expect(onSend).toHaveBeenCalledWith('Test message', 'test-conversation-id')
    })
  })

  describe('Red Phase: Responsive Design', () => {
    test('positions mode switch appropriately on small screens', () => {
      // Set mobile viewport size
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 480,
      })
      
      renderWithContext(
        <QuestionInput
          {...defaultProps}
          useModernRag={false}
          onModeChange={jest.fn()}
        />
      )

      const modeSwitchContainer = screen.getByTestId('mode-switch-container')
      expect(modeSwitchContainer).toBeInTheDocument()
      
      // Check that the container exists (CSS class verification in real scenario would be through visual testing)
    })
  })

  // 🆕 Phase 2: UI Improvements - TDD for new requirements
  describe('Red Phase: UI Improvements', () => {
    test('hides toggle text labels (Chat/Web検索) while keeping tooltip', async () => {
      const user = userEvent.setup()
      
      renderWithContext(
        <QuestionInput
          {...defaultProps}
          useModernRag={false}
          onModeChange={jest.fn()}
        />
      )

      const modeSwitch = screen.getByTestId('mode-toggle')
      
      // Text labels should not be visible in the DOM
      expect(screen.queryByText('Chat')).not.toBeInTheDocument()
      expect(screen.queryByText('Web検索')).not.toBeInTheDocument()
      
      // But tooltip should still work
      await user.hover(modeSwitch)
      await waitFor(() => {
        const tooltipElements = screen.getAllByText(/Chatモード: Azure OpenAI による標準的な会話/)
        const visibleTooltip = tooltipElements.find(element => !element.hidden)
        expect(visibleTooltip).toBeInTheDocument()
      })
    })

    test('removes background styling from toggle switch container', () => {
      renderWithContext(
        <QuestionInput
          {...defaultProps}
          useModernRag={false}
          onModeChange={jest.fn()}
        />
      )

      const modeSwitchContainer = screen.getByTestId('mode-switch-container')
      
      // Container should exist but without background styling
      expect(modeSwitchContainer).toBeInTheDocument()
      expect(modeSwitchContainer).toHaveAttribute('data-testid', 'mode-switch-container')
      
      // Check that no background class is applied (test implementation will verify this)
      expect(modeSwitchContainer).not.toHaveClass('backgroundStyle')
    })

    test('positions toggle switch in appropriate location (image upload disabled)', () => {
      renderWithContext(
        <QuestionInput
          {...defaultProps}
          useModernRag={false}
          onModeChange={jest.fn()}
          disableImageUpload={true}  // 画像アップロードを無効化
        />
      )

      const modeSwitchContainer = screen.getByTestId('mode-switch-container')
      
      // 画像アップロードが無効になっているため、アイコンは表示されない
      const imageUploadLabel = screen.queryByLabelText('Upload Image')
      expect(imageUploadLabel).not.toBeInTheDocument()
      
      // Position verification will be done through CSS classes and visual testing
      // Here we verify the elements exist and container has the correct positioning class
      expect(modeSwitchContainer).toHaveAttribute('data-position', 'above-image-icon')
    })
  })

  // 🆕 Phase 2: Layout Alignment Tests (Red Phase)
  describe('Red Phase: Right-side Alignment Tests', () => {
    test('should align toggle switch with image upload and send button horizontally (FAILING)', () => {
      renderWithContext(
        <QuestionInput
          {...defaultProps}
          useModernRag={false}
          onModeChange={jest.fn()}
        />
      )

      const toggleContainer = screen.getByTestId('mode-switch-container')
      
      // 右側配置用のdata属性を確認（まだ実装していないので失敗する）
      expect(toggleContainer).toHaveAttribute('data-layout', 'right-aligned')
    })

    test('should arrange toggle, image upload, and send button vertically (FAILING)', () => {
      renderWithContext(
        <QuestionInput
          {...defaultProps}
          useModernRag={false}
          onModeChange={jest.fn()}
        />
      )

      const toggleContainer = screen.getByTestId('mode-switch-container')
      
      // 縦配置用のdata属性を確認（まだ実装していないので失敗する）
      expect(toggleContainer).toHaveAttribute('data-vertical-order', 'top')
    })

    test('should fit all controls within chat input area without overflow (FAILING)', () => {
      renderWithContext(
        <QuestionInput
          {...defaultProps}
          useModernRag={false}
          onModeChange={jest.fn()}
        />
      )

      const toggleContainer = screen.getByTestId('mode-switch-container')
      
      // オーバーフロー対策のdata属性を確認（まだ実装していないので失敗する）
      expect(toggleContainer).toHaveAttribute('data-contained', 'true')
    })
  })

  // 🆕 Phase 3: Image Upload Hiding Tests (Red Phase)
  describe('Red Phase: Image Upload Icon Hiding', () => {
    test('should hide image upload icon to prevent errors (FAILING)', () => {
      renderWithContext(
        <QuestionInput
          {...defaultProps}
          useModernRag={false}
          onModeChange={jest.fn()}
        />
      )

      // 画像アップロードアイコンが非表示になっていることを確認
      const imageUploadElements = screen.queryAllByLabelText('Upload Image')
      expect(imageUploadElements).toHaveLength(0)
    })

    test('should not render file input when image upload is disabled (FAILING)', () => {
      renderWithContext(
        <QuestionInput
          {...defaultProps}
          useModernRag={false}
          onModeChange={jest.fn()}
        />
      )

      // ファイル入力要素が存在しないことを確認
      const fileInput = screen.queryByTestId('file-input')
      expect(fileInput).not.toBeInTheDocument()
    })

    test('should show image upload icon when not disabled', () => {
      renderWithContext(
        <QuestionInput
          {...defaultProps}
          useModernRag={false}
          onModeChange={jest.fn()}
          disableImageUpload={false}  // 明示的に画像アップロードを有効化
        />
      )

      // 画像アップロードアイコンが表示されることを確認
      const imageUploadElements = screen.queryAllByLabelText('Upload Image')
      expect(imageUploadElements.length).toBeGreaterThan(0)
    })
  })
})