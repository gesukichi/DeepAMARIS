import { useContext, useMemo, useState } from 'react'
import { FontIcon, Stack, Text, TextField, TooltipHost, DirectionalHint, Dropdown, IDropdownOption } from '@fluentui/react'
import { SendRegular } from '@fluentui/react-icons'

import Send from '../../assets/Send.svg'

import styles from './QuestionInput.module.css'
import { ChatMessage } from '../../api'
import { AppStateContext } from '../../state/AppProvider'
import { resizeImage } from '../../utils/resizeImage'

type ModeOption = {
  id: string
  title: string
  description: string
  endpoint?: string
}

interface Props {
  onSend: (question: ChatMessage['content'], id?: string) => void
  disabled: boolean
  placeholder?: string
  clearOnSend?: boolean
  conversationId?: string
  chatMode?: string
  modeOptions?: ModeOption[]
  onModeChange?: (modeId: string) => void
  // 🆕 画像アップロード制御props
  disableImageUpload?: boolean
}

export const QuestionInput = ({ 
  onSend, 
  disabled, 
  placeholder, 
  clearOnSend, 
  conversationId,
  chatMode,
  modeOptions,
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

  const availableModeOptions = useMemo(() => modeOptions ?? [], [modeOptions])
  const selectedModeId = chatMode || availableModeOptions[0]?.id
  const selectedMode = useMemo(
    () => availableModeOptions.find(option => option.id === selectedModeId) ?? availableModeOptions[0],
    [availableModeOptions, selectedModeId]
  )

  const handleModeChange = (_ev: React.FormEvent<HTMLDivElement>, option?: IDropdownOption) => {
    if (onModeChange && option?.key) {
      onModeChange(option.key as string)
    }
  }

  const dropdownOptions: IDropdownOption<ModeOption>[] = availableModeOptions.map(option => ({
    key: option.id,
    text: option.title,
    data: option
  }))

  const getModeDescription = (): string => {
    return selectedMode?.description || "利用するチャットモードを選択してください"
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
      
      {/* 🆕 モード切り替えセレクター */}
      {onModeChange && dropdownOptions.length > 0 && (
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
            <Dropdown
              ariaLabel={`現在のモード: ${selectedMode?.title ?? 'モード未選択'}`}
              selectedKey={selectedModeId}
              options={dropdownOptions}
              onChange={handleModeChange}
              data-testid="mode-toggle"
              className={styles.modeToggleDropdown}
              onRenderOption={option => (
                <div className={styles.modeOption}>
                  <Text className={styles.modeOptionTitle}>{option?.text}</Text>
                  {option?.data?.description && (
                    <Text variant="small" className={styles.modeOptionDescription}>
                      {option.data.description}
                    </Text>
                  )}
                </div>
              )}
              onRenderTitle={items => {
                const option = items?.[0]
                return option ? (
                  <div className={styles.modeSelectedTitle}>
                    <Text className={styles.modeOptionTitle}>{option.text}</Text>
                    {selectedMode?.description && (
                      <Text variant="small" className={styles.modeOptionDescription}>
                        {selectedMode.description}
                      </Text>
                    )}
                  </div>
                ) : null
              }}
            />
          </TooltipHost>
        </div>
      )}
      
      <div className={styles.questionInputBottomBorder} />
    </Stack>
  )
}
