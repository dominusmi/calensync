// const fs = require('fs');
import fs from 'fs';

function generateSitemapXML(host, languages, paths, extraPaths) {
  // host must not contain the trailing "/"
  let xml = '<?xml version="1.0" encoding="UTF-8"?>\n';
  xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n';

  paths.forEach(path => {
    languages.forEach(lang => {
      const url = `${host}${lang}${path}`;
      xml += `  <url>\n`;
      xml += `    <loc>${url}</loc>\n`;

      if(lang !== '/en'){
        xml += `    <xhtml:link rel="canonical" href="${host}${lang}${path}" />\n`;
      }else{
        xml += `    <xhtml:link rel="canonical" href="${host}${path}" />\n`;
      }

      languages.forEach(hrefLang => {
        if (hrefLang !== lang && hrefLang !== '') {
          const alternateUrl = `${host}${hrefLang}${path}`;
          xml += `    <xhtml:link rel="alternate" hreflang="${hrefLang.slice(1)}" href="${alternateUrl}" />\n`;
        }
      });

      xml += `  </url>\n`;
    });
  });

  
  Object.values(extraPaths).map(routes => {
    Object.keys(routes).map(lang => {
      const path = routes[lang].url;
      xml += `  <url>\n`;
      xml += `    <loc>${host}${path}</loc>\n`;
      xml += `    <xhtml:link rel="canonical" href="${host}${path}" />\n`;

      Object.entries((routes)).map(([alternativeLang, {url}]) => {
        if(alternativeLang == lang) { return }
        xml += `    <xhtml:link rel="alternate" hreflang="${alternativeLang}" href="${host}${url}" />\n`;
      })
      xml += `  </url>\n`;
    })
  })

  xml += '</urlset>';
  return xml;
}

// Example Usage:
const languages = ['', '/en', '/fr', '/it'];
const paths = [
  '/',
  '/dashboard',
  '/login',
  '/plan',
  '/tos',
  '/privacy',
  '/google-privacy',
  '/for-freelancers',
  '/blog'
];


try {
  // extract routes. This is horrible, but setting up a typescript script is horribler
  const content = fs.readFileSync("src/_blog/routes.tsx").toString();
  const routes = JSON.parse(content.split("\n").at(-1).split("= ")[1]);
  const host = process.argv.at(2) ?? "http://127.0.0.1:8080"
  const resultXML = generateSitemapXML(host, [''], paths, routes);
  fs.writeFileSync('sitemap.xml', resultXML);
} catch (error) {
  console.error("Error parsing the array argument:", error.message);
  process.exit(1);
}
