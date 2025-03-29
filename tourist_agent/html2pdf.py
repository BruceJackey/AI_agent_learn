import asyncio
from pyppeteer import launch

async def html_to_pdf(html_path, output_pdf):
    browser = await launch()
    page = await browser.newPage()
    await page.goto(f'file://{html_path}', waitUntil='networkidle0')
    await page.pdf({'path': output_pdf, 'format': 'A4'})
    await browser.close()

# 运行转换
html_path = 'D:/agent/storage/上海3天旅游攻略.html'
asyncio.get_event_loop().run_until_complete(html_to_pdf(html_path, 'output.pdf'))