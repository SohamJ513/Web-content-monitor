// frontend/src/pages/DirectFactCheckPage.tsx
import React, { useState } from 'react';
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  Card,
  CardContent,
  Chip,
  Alert,
  CircularProgress,
  IconButton,
  Tooltip,
  Divider
} from '@mui/material';
import {
  ContentPaste,
  Clear,
  PlayArrow,
  HelpOutline,
  Article,
  Link as LinkIcon,
  Title
} from '@mui/icons-material';
import { factCheckApi } from '../services/factCheckApi';
import { FactCheckResponse, DirectFactCheckRequest } from '../types/factCheck';
import FactCheckResults from '../components/FactCheck/FactCheckResults';

const DirectFactCheckPage: React.FC = () => {
  const [content, setContent] = useState('');
  const [pageUrl, setPageUrl] = useState('');
  const [pageTitle, setPageTitle] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<FactCheckResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFactCheck = async () => {
    if (!content.trim()) {
      setError('Please enter some content to fact-check');
      return;
    }

    setIsLoading(true);
    setError(null);
    
    try {
      const request: DirectFactCheckRequest = {
        content: content,
        page_url: pageUrl || 'Direct input',
        page_title: pageTitle || 'User provided content',
      };

      const data = await factCheckApi.checkDirectContent(request);
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fact checking failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleClear = () => {
    setContent('');
    setPageUrl('');
    setPageTitle('');
    setResult(null);
    setError(null);
  };

  const sampleTechnicalContent = `Python 3.6 offers 50% better performance than Python 2.7 and requires only 1GB of RAM. 
React 16 is compatible with Node.js 12 which provides 3x faster startup times. 
Using blockchain technology makes applications completely secure from all cyber attacks.
Django 2.2 is fully supported and recommended for all production applications.`;

  const loadSampleContent = () => {
    setContent(sampleTechnicalContent);
    setPageTitle('Sample Technical Content');
    setPageUrl('https://example.com/sample');
  };

  const pasteFromClipboard = async () => {
    try {
      const text = await navigator.clipboard.readText();
      setContent(text);
    } catch (err) {
      setError('Unable to paste from clipboard');
    }
  };

  return (
    <Box sx={{ p: 3, maxWidth: 1200, margin: '0 auto' }}>
      {/* Header Section */}
      <Box sx={{ mb: 4, textAlign: 'center' }}>
        <Typography 
          variant="h4" 
          component="h1" 
          gutterBottom 
          sx={{ 
            fontWeight: 'bold',
            background: 'linear-gradient(135deg, #2563eb 0%, #1e40af 100%)',
            backgroundClip: 'text',
            WebkitBackgroundClip: 'text',
            color: 'transparent'
          }}
        >
          Direct Content Fact Checker
        </Typography>
        <Typography variant="h6" color="text.secondary" sx={{ mb: 2 }}>
          Analyze technical content for accuracy and verify claims
        </Typography>
        <Chip 
          icon={<ContentPaste />} 
          label="Paste content directly when crawling fails" 
          variant="outlined"
          color="primary"
        />
      </Box>

      {/* Main Content - Using Flex instead of Grid */}
      <Box sx={{ display: 'flex', gap: 3, flexDirection: { xs: 'column', md: 'row' } }}>
        {/* Input Section */}
        <Box sx={{ flex: 2 }}>
          <Paper elevation={2} sx={{ p: 3 }}>
            {/* URL and Title Inputs */}
            <Box sx={{ mb: 3 }}>
              <Typography 
                variant="h6" 
                gutterBottom 
                sx={{ display: 'flex', alignItems: 'center', gap: 1 }}
              >
                <LinkIcon color="primary" />
                Source Information
              </Typography>
              <Box sx={{ display: 'flex', gap: 2, flexDirection: { xs: 'column', sm: 'row' } }}>
                <TextField
                  fullWidth
                  label="Page URL"
                  value={pageUrl}
                  onChange={(e) => setPageUrl(e.target.value)}
                  placeholder="https://example.com/article"
                  InputProps={{
                    startAdornment: <LinkIcon sx={{ color: 'text.secondary', mr: 1 }} />
                  }}
                />
                <TextField
                  fullWidth
                  label="Page Title"
                  value={pageTitle}
                  onChange={(e) => setPageTitle(e.target.value)}
                  placeholder="Technical Article Title"
                  InputProps={{
                    startAdornment: <Title sx={{ color: 'text.secondary', mr: 1 }} />
                  }}
                />
              </Box>
            </Box>

            {/* Content Textarea */}
            <Box sx={{ mb: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                <Typography 
                  variant="h6" 
                  sx={{ display: 'flex', alignItems: 'center', gap: 1 }}
                >
                  <Article color="primary" />
                  Technical Content
                </Typography>
                <Box>
                  <Tooltip title="Load sample content">
                    <Button 
                      startIcon={<ContentPaste />} 
                      onClick={loadSampleContent}
                      size="small"
                      variant="outlined"
                      sx={{ mr: 1 }}
                    >
                      Sample
                    </Button>
                  </Tooltip>
                  <Tooltip title="Paste from clipboard">
                    <IconButton onClick={pasteFromClipboard} size="small">
                      <ContentPaste />
                    </IconButton>
                  </Tooltip>
                </Box>
              </Box>
              
              <TextField
                multiline
                rows={12}
                fullWidth
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="Paste technical blog content, documentation, or article text here..."
                disabled={isLoading}
                sx={{
                  '& .MuiOutlinedInput-root': {
                    fontFamily: 'monospace',
                    fontSize: '0.9rem'
                  }
                }}
              />
              
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1 }}>
                <Typography variant="body2" color="text.secondary">
                  {content.length} characters • {content.split(/\s+/).filter(word => word.length > 0).length} words
                </Typography>
                {content.length > 0 && (
                  <Chip 
                    label={`${Math.ceil(content.length / 1500)} min read`} 
                    size="small" 
                    variant="outlined" 
                  />
                )}
              </Box>
            </Box>

            {/* Action Buttons */}
            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
              <Button
                onClick={handleClear}
                startIcon={<Clear />}
                variant="outlined"
                disabled={isLoading}
                size="large"
              >
                Clear All
              </Button>
              <Button
                onClick={handleFactCheck}
                disabled={isLoading || !content.trim()}
                variant="contained"
                startIcon={isLoading ? <CircularProgress size={20} /> : <PlayArrow />}
                size="large"
                sx={{
                  background: 'linear-gradient(135deg, #2563eb 0%, #1e40af 100%)',
                  minWidth: 200,
                  '&:hover': {
                    background: 'linear-gradient(135deg, #1e40af 0%, #1e3a8a 100%)',
                  }
                }}
              >
                {isLoading ? 'Analyzing Content...' : 'Check Technical Facts'}
              </Button>
            </Box>

            {error && (
              <Alert severity="error" sx={{ mt: 2 }}>
                {error}
              </Alert>
            )}
          </Paper>
        </Box>

        {/* Results & Help Section */}
        <Box sx={{ flex: 1, minWidth: { md: 350 } }}>
          {result ? (
            <FactCheckResults data={result} />
          ) : (
            <Card 
              elevation={2} 
              sx={{ background: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)' }}
            >
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <HelpOutline color="primary" sx={{ mr: 1 }} />
                  <Typography variant="h6" component="h2">
                    How to Use
                  </Typography>
                </Box>
                
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <Box>
                    <Typography variant="subtitle2" color="primary" gutterBottom>
                      📝 Content Guidelines
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Paste technical blogs, documentation, or articles containing specific claims about:
                    </Typography>
                    <Box component="ul" sx={{ pl: 2, mt: 1 }}>
                      <Typography variant="body2" component="li" color="text.secondary">
                        Version compatibility
                      </Typography>
                      <Typography variant="body2" component="li" color="text.secondary">
                        Performance benchmarks
                      </Typography>
                      <Typography variant="body2" component="li" color="text.secondary">
                        Security claims
                      </Typography>
                      <Typography variant="body2" component="li" color="text.secondary">
                        API specifications
                      </Typography>
                    </Box>
                  </Box>

                  <Divider />

                  <Box>
                    <Typography variant="subtitle2" color="primary" gutterBottom>
                      ⚡ Quick Tips
                    </Typography>
                    <Box component="ul" sx={{ pl: 2 }}>
                      <Typography variant="body2" component="li" color="text.secondary">
                        Use when webpage crawling fails
                      </Typography>
                      <Typography variant="body2" component="li" color="text.secondary">
                        Try sample content for a demo
                      </Typography>
                      <Typography variant="body2" component="li" color="text.secondary">
                        Include specific numbers and versions
                      </Typography>
                    </Box>
                  </Box>

                  <Button
                    onClick={loadSampleContent}
                    variant="outlined"
                    fullWidth
                    startIcon={<ContentPaste />}
                    sx={{ mt: 1 }}
                  >
                    Load Sample Content
                  </Button>
                </Box>
              </CardContent>
            </Card>
          )}
        </Box>
      </Box>
    </Box>
  );
};

export default DirectFactCheckPage;