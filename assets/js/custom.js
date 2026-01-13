if (window.Telegram?.WebApp) {
  const tg = Telegram.WebApp;
  tg.ready();
  tg.expand();

  // Цвета header/background из TG-темы
  tg.setHeaderColor(tg.themeParams.header_bg_color);
  tg.setBackgroundColor(tg.themeParams.bg_color);

  // MainButton для CTA (например, "Подробнее")
  tg.MainButton.text = "Открыть пост";
  tg.MainButton.color = tg.themeParams.button_color;
  tg.MainButton.textColor = tg.themeParams.button_text_color;
  tg.MainButton.isVisible = true;
  tg.MainButton.onClick(() => {
    tg.HapticFeedback.impactOccurred('medium'); // Вибрация
    // Логика: перейти к посту или отправить данные боту
  });

  // BackButton
  tg.BackButton.onClick(() => tg.close());

  // Смена темы
  tg.onEvent('themeChanged', () => document.documentElement.setAttribute('data-theme', tg.colorScheme));
}
