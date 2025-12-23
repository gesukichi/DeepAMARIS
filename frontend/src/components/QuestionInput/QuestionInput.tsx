import { useContext, useState } from 'react'
import { FontIcon, Stack, TextField, Toggle, TooltipHost, DirectionalHint } from '@fluentui/react'
import { SendRegular } from '@fluentui/react-icons'

import Send from '../../assets/Send.svg'

import styles from './QuestionInput.module.css'
import { ChatMessage } from '../../api'
import { AppStateContext } from '../../state/AppProvider'
import { resizeImage } from '../../utils/resizeImage'

interface Props {
  onSend: (question: ChatMessage['content'], id?: string) => void
  disabled: boolean
  placeholder?: string
  clearOnSend?: boolean
  conversationId?: string
  // 🆕 モード切り替え関連props
  useModernRag?: boolean
  onModeChange?: (useModernRag: boolean) => void
  // 🆕 画像アップロード制御props
  disableImageUpload?: boolean
}

export const QuestionInput = ({ 
  onSend, 
  disabled, 
  placeholder, 
  clearOnSend, 
  conversationId,
  useModernRag = false,
  onModeChange,
  disableImageUpload = false
}: Props) => {
  const [question, setQuestion] = useState<string>('')
  const [base64Image, setBase64Image] = useState<string | null>(null);

  const appStateContext = useContext(AppStateContext)
  const OYD_ENABLED = appStateContext?.state.frontendSettings?.oyd_enabled || false;

  const handleImageUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];

    if (file) {
      await convertToBase64(file);
    }
  };

  const convertToBase64 = async (file: Blob) => {
    try {
      const resizedBase64 = await resizeImage(file, 800, 800);
      setBase64Image(resizedBase64);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  const sendQuestion = () => {
    if (disabled || !question.trim()) {
      return
    }

    const questionTest: ChatMessage["content"] = base64Image ? [{ type: "text", text: question }, { type: "image_url", image_url: { url: base64Image } }] : question.toString();

    if (conversationId && questionTest !== undefined) {
      onSend(questionTest, conversationId)
      setBase64Image(null)
    } else {
      onSend(questionTest)
      setBase64Image(null)
    }

    if (clearOnSend) {
      setQuestion('')
    }
  }

  const onEnterPress = (ev: React.KeyboardEvent<Element>) => {
    if (ev.key === 'Enter' && !ev.shiftKey && !(ev.nativeEvent?.isComposing === true)) {
      ev.preventDefault()
      sendQuestion()
    }
  }

  // モード切り替えハンドラー
  const handleModeChange = (_ev: React.FormEvent<HTMLElement>, checked?: boolean) => {
    if (onModeChange) {
      onModeChange(checked || false)
    }
  }

  // ツールチップ用のモード説明テキスト
  const getModeDescription = (): string => {
    return useModernRag 
      ? "Chat + Web検索統合モード: ドキュメント検索とWeb検索を組み合わせた高度な情報取得"
      : "Chatモード: Azure OpenAI による標準的な会話"
  }

  const onQuestionChange = (_ev: React.FormEvent<HTMLInputElement | HTMLTextAreaElement>, newValue?: string) => {
    setQuestion(newValue || '')
  }

  const sendQuestionDisabled = disabled || !question.trim()

  return (
    <Stack horizontal className={styles.questionInputContainer}>
      <TextField
        className={styles.questionInputTextArea}
        placeholder={placeholder}
        multiline
        resizable={false}
        borderless
        value={question}
        onChange={onQuestionChange}
        onKeyDown={onEnterPress}
      />
      {/* 画像アップロード機能の表示制御 */}
      {!disableImageUpload && !OYD_ENABLED && (
        <div className={styles.fileInputContainer}>
          <input
            type="file"
            id="fileInput"
            onChange={(event) => handleImageUpload(event)}
            accept="image/*"
            className={styles.fileInput}
            data-testid="file-input"
          />
          <label htmlFor="fileInput" className={styles.fileLabel} aria-label='Upload Image'>
            <FontIcon
              className={styles.fileIcon}
              iconName={'PhotoCollection'}
              aria-label='Upload Image'
            />
          </label>
        </div>)}
      {base64Image && <img className={styles.uploadedImage} src={base64Image} alt="Uploaded Preview" />}
      <div
        className={styles.questionInputSendButtonContainer}
        role="button"
        tabIndex={0}
        aria-label="Ask question button"
        onClick={sendQuestion}
        onKeyDown={e => (e.key === 'Enter' || e.key === ' ' ? sendQuestion() : null)}>
        {sendQuestionDisabled ? (
          <SendRegular className={styles.questionInputSendButtonDisabled} />
        ) : (
          <img src={Send} className={styles.questionInputSendButton} alt="Send Button" />
        )}
      </div>
      
      {/* 🆕 モード切り替えスイッチ */}
      {onModeChange && (
        <div 
          className={styles.modeSwitchContainer} 
          data-testid="mode-switch-container" 
          data-position="above-image-icon"
          data-layout="right-aligned"
          data-vertical-order="top"
          data-contained="true"
        >
          <TooltipHost
            content={getModeDescription()}
            directionalHint={DirectionalHint.topCenter}
            delay={0}
          >
            <Toggle
              checked={useModernRag}
              onChange={handleModeChange}
              onText=""
              offText=""
              className={styles.modeToggle}
              ariaLabel={`現在のモード: ${useModernRag ? 'Web検索統合' : 'Chat'}`}
              data-testid="mode-toggle"
            />
          </TooltipHost>
        </div>
      )}
      
      <div className={styles.questionInputBottomBorder} />
    </Stack>
  )
}
