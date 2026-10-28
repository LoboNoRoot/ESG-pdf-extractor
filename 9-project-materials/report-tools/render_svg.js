const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe'
  });
  const page = await browser.newPage({ viewport: { width: 2200, height: 920 }, deviceScaleFactor: 1 });
  await page.goto('file:///C:/Users/Lenovo/Desktop/%E7%9C%81%E4%B8%80%E6%94%B9/tmp/report_assets/%E4%BC%81%E4%B8%9A%E7%AB%AF%E5%88%B0%E7%AB%AF%E4%BA%A4%E4%BB%98%E9%97%AD%E7%8E%AF%E5%9B%BE.svg');
  await page.screenshot({ path: 'C:/Users/Lenovo/Desktop/省一改/tmp/report_assets/flow-qa.png', fullPage: true });
  await browser.close();
})();
