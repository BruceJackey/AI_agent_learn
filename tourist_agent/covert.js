// const puppeteer = require('puppeteer');
// const path = require('path');

// (async () => {
//   const browser = await puppeteer.launch();
//   const page = await browser.newPage();
  
//   // 本地HTML文件路径（需转换为file://格式）
//   const htmlPath = path.resolve('D:/agent/storage/上海3天旅游攻略.html');
//   await page.goto(`file://${htmlPath}`, { waitUntil: 'networkidle0' });
  
//   // 生成PDF
//   await page.pdf({
//     path: 'output.pdf',
//     format: 'A4',
//     printBackground: true, // 保留背景颜色和图片
//   });
  
//   await browser.close();
//   console.log('PDF已生成！');
// })();
console.log("Hello Node.js!");