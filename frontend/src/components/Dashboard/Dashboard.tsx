import React, { useState, useEffect } from 'react';
import { Typography, Box, Alert, CircularProgress, Snackbar } from '@mui/material';
import { pagesAPI, TrackedPage, crawlAPI } from '../../services/api';
import AddPageForm from './AddPageForm';
import PageList from './PageList';

const Dashboard: React.FC = () => {
  const [pages, setPages] = useState<TrackedPage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [crawling, setCrawling] = useState<Set<string>>(new Set()); // Track which pages are being crawled
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'info';
  }>({
    open: false,
    message: '',
    severity: 'success',
  });

  const fetchPages = async () => {
    try {
      const response = await pagesAPI.getAll();
      console.log('Fetched pages:', response.data);
      setPages(response.data);
      setError('');
    } catch (err: any) {
      console.error('Fetch pages error:', err);
      setError(err.response?.data?.detail || 'Failed to fetch pages');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPages();
  }, []);

  const handlePageAdded = (newPage: TrackedPage) => {
    setPages((prev) => [newPage, ...prev]);
    setSnackbar({
      open: true,
      message: 'Page added successfully!',
      severity: 'success',
    });
  };

  const handlePageDeleted = (pageId: string) => {
    setPages((prev) => prev.filter((page) => page.id !== pageId));
    setSnackbar({
      open: true,
      message: 'Page deleted successfully!',
      severity: 'info',
    });
  };

  const handlePageUpdated = (updatedPage: TrackedPage) => {
    setPages((prev) =>
      prev.map((page) => (page.id === updatedPage.id ? updatedPage : page))
    );
  };

  // ✅ Fixed crawl handler to match actual backend response
  const handleCrawl = async (pageId: string) => {
    if (crawling.has(pageId)) {
      return; // Prevent multiple simultaneous crawls
    }

    setCrawling(prev => new Set(prev).add(pageId));
    
    try {
      console.log(`Starting crawl for page: ${pageId}`);
      
      // ✅ Use the correct API method
      const response = await crawlAPI.crawlPage(pageId);
      const result = response.data;
      
      console.log('Crawl response:', result);

      // ✅ Show success message with actual backend response structure
      const changeStatus = result.change_detected ? 'Change detected!' : 'No changes';
      setSnackbar({
        open: true,
        message: `Crawl completed! ${changeStatus} (Version: ${result.version_id})`,
        severity: result.change_detected ? 'success' : 'info',
      });

      // ✅ Refresh pages to get updated last_checked, etc.
      await fetchPages();
      
    } catch (err: any) {
      console.error('Crawl error:', err);
      const errorMessage = err.response?.data?.detail || 'Crawl failed';
      setSnackbar({
        open: true,
        message: errorMessage,
        severity: 'error',
      });
    } finally {
      setCrawling(prev => {
        const newSet = new Set(prev);
        newSet.delete(pageId);
        return newSet;
      });
    }
  };

  const closeSnackbar = () => {
    setSnackbar(prev => ({ ...prev, open: false }));
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
        <CircularProgress />
        <Typography variant="body2" sx={{ ml: 2 }}>
          Loading your monitored pages...
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      <Box sx={{ mb: 3 }}>
        <AddPageForm onPageAdded={handlePageAdded} />
      </Box>

      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">
          Monitored Pages ({pages.length})
        </Typography>
        
        {pages.length > 0 && (
          <Typography variant="body2" color="text.secondary">
            {pages.filter(p => p.is_active).length} active • {' '}
            {pages.filter(p => p.last_change_detected).length} with changes
          </Typography>
        )}
      </Box>

      {pages.length === 0 ? (
        <Alert severity="info" sx={{ mt: 2 }}>
          No pages being monitored yet. Add your first page above to get started!
        </Alert>
      ) : (
        <PageList
          pages={pages}
          onPageDeleted={handlePageDeleted}
          onPageUpdated={handlePageUpdated}
          onPageCrawl={handleCrawl}
          crawlingPages={crawling} // ✅ Pass crawling state to show loading indicators
        />
      )}

      {/* ✅ Enhanced Snackbar for better feedback */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={closeSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          severity={snackbar.severity}
          sx={{ width: '100%' }}
          onClose={closeSnackbar}
          variant="filled"
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default Dashboard;