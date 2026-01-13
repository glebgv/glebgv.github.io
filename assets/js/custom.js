if (window.Telegram?.WebApp?.initDataUnsafe) {
  Telegram.WebApp.ready();
  Telegram.WebApp.expand(); // Полноэкранный режим
  // Применяем цвета к header/background TG
  Telegram.WebApp.setHeaderColor('#5288c1'); // Или из themeParams.button_color
  Telegram.WebApp.setBackgroundColor('#17212b');
  // Обработчик смены темы
  Telegram.WebApp.onEvent('themeChanged', () => {
    document.body.classList.toggle('dark', Telegram.WebApp.themeParams.bg_color === '#17212b'); // Пример логики
  });
}

