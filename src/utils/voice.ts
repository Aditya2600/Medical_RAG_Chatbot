export const isSpeechRecognitionSupported = (): boolean => {
  if (typeof window === 'undefined') return false;
  return Boolean(window.SpeechRecognition || window.webkitSpeechRecognition);
};

export const getSpeechRecognition = (): SpeechRecognition | null => {
  if (typeof window === 'undefined') return null;
  const SpeechRecognitionConstructor =
    window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognitionConstructor) return null;
  return new SpeechRecognitionConstructor();
};

export const isSpeechSynthesisSupported = (): boolean => {
  if (typeof window === 'undefined') return false;
  return (
    'speechSynthesis' in window &&
    'SpeechSynthesisUtterance' in window &&
    typeof window.speechSynthesis?.speak === 'function'
  );
};

export const speakText = (text: string): boolean => {
  if (!isSpeechSynthesisSupported()) return false;
  const trimmed = text.trim();
  if (!trimmed) return false;

  const utterance = new SpeechSynthesisUtterance(trimmed);
  if (typeof navigator !== 'undefined' && navigator.language) {
    utterance.lang = navigator.language;
  }
  utterance.rate = 1;
  utterance.pitch = 1;

  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
  return true;
};

export const stopSpeaking = (): void => {
  if (!isSpeechSynthesisSupported()) return;
  window.speechSynthesis.cancel();
};
