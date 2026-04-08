# 🚀 GitHub Pages Deployment Guide

## Quick Start (5 minutes!)

### Method 1: Direct Upload
1. **Download** the zip file
2. **Extract** all files
3. **Upload** to your GitHub repository
4. Go to **Settings** → **Pages**
5. Set source to **Deploy from a branch**
6. Choose **main** branch and **/ (root)**
7. **Save** and wait 2-3 minutes
8. Your site is live! 🎉

### Method 2: Git Commands
```bash
git clone https://github.com/yourusername/your-repo.git
cd your-repo
# Copy all files from extracted zip into this folder
git add .
git commit -m "🚀 Deploy Hyperfocus Support page"
git push origin main
```

## ⚙️ Configuration Checklist

### Before Going Live:
- [ ] Update all donation links with your actual URLs
- [ ] Replace placeholder email addresses
- [ ] Add your real Discord invite link
- [ ] Update supporter count numbers
- [ ] Test all donation buttons
- [ ] Check mobile responsiveness
- [ ] Verify accessibility features work

### Custom Domain (Optional):
1. Add `CNAME` file with your domain
2. Configure DNS A records:
   - `185.199.108.153`
   - `185.199.109.153`
   - `185.199.110.153`
   - `185.199.111.153`

## 🎨 Quick Customizations

### Change Colors:
Edit `css/styles.css` - look for `:root` variables at the top.

### Update Metrics:
Edit `js/main.js` - find the `baseValues` object around line 150.

### Modify Content:
Edit `index.html` - all text content is clearly structured.

## 🔍 Testing Your Site

### Accessibility Test:
1. Tab through entire page (keyboard only)
2. Test screen reader with NVDA/JAWS
3. Try the accessibility toggles
4. Check color contrast

### Performance Test:
1. Open Chrome DevTools
2. Run Lighthouse audit
3. Aim for 90+ scores
4. Test on mobile device

### PWA Test:
1. Open in Chrome/Edge
2. Look for install prompt
3. Test offline functionality
4. Verify manifest loads correctly

## 📊 Analytics Setup

### Google Analytics:
Add this to `js/main.js` in the `trackEvent` function:
```javascript
if (typeof gtag !== 'undefined') {
    gtag('event', eventName, properties);
}
```

### Add GA tag to `index.html` head:
```html
<script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'GA_MEASUREMENT_ID');
</script>
```

## 🚨 Troubleshooting

### Site Not Loading?
- Check GitHub Pages is enabled
- Verify main branch is selected
- Wait 5-10 minutes for propagation
- Check for HTML syntax errors

### PWA Not Installing?
- Must be served over HTTPS (GitHub Pages provides this)
- Check manifest.json is valid
- Verify service worker registers
- Test in Chrome/Edge (best PWA support)

### Accessibility Issues?
- Validate HTML with W3C validator
- Check aria-labels are present
- Verify keyboard navigation works
- Test with actual screen reader

## 📱 Mobile Optimization

The page is already mobile-optimized, but to enhance further:
1. Test on real devices
2. Check touch targets (44px minimum)
3. Verify text is readable without zoom
4. Test form inputs on mobile keyboards

## 🎯 Conversion Tips

### Immediate Wins:
- Add urgency ("Only 23 spots left this month!")
- Show recent supporter activity
- Include specific impact numbers
- Use testimonials prominently

### Advanced:
- A/B test button colors/text
- Add exit-intent popups
- Implement donation progress tracking
- Create supporter milestone celebrations

## 🔐 Security Notes

- No sensitive data in client-side code
- All external links use `rel="noopener noreferrer"`
- Service worker only caches safe resources
- PWA permissions are minimal

---

**Need help?** Drop questions in the Discord or open a GitHub issue!

**Ready to go live?** The page is production-ready! 🚀
