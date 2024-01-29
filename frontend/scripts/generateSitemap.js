const fs = require('fs');

function generateSitemapXML(languages, paths) {
    let xml = '<?xml version="1.0" encoding="UTF-8"?>\n';
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n';
  
    languages.forEach(lang => {
      paths.forEach(path => {
        const url = `http://127.0.0.1:8080/${lang}${path}`;
        xml += `  <url>\n`;
        xml += `    <loc>${url}</loc>\n`;
  
        languages.forEach(hrefLang => {
          if (hrefLang !== lang) {
            const alternateUrl = `http://127.0.0.1:8080/${hrefLang}${path}`;
            xml += `    <xhtml:link rel="alternate" hreflang="${hrefLang}" href="${alternateUrl}" />\n`;
          }
        });
  
        xml += `  </url>\n`;
      });
    });
  
    xml += '</urlset>';
    return xml;
  }
  
  // Example Usage:
  const languages = ['en', 'fr', 'it'];
  const paths = [
    '/',
    '/dashboard',
    '/login',
    '/plan',
    '/tos',
    '/privacy',
    '/google-privacy',
    '/for-freelancers',
    '/blog/sync-multiple-google-calendars',
    '/blog/avoid-calendly-conflicts',
    '/blog/sync-all-google-calendars-into-one'
  ];
  
  const resultXML = generateSitemapXML(languages, paths);
  fs.writeFileSync('sitemap.xml', resultXML);