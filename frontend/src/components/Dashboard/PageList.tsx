import React from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Button,
  Chip,
  Tooltip,
  CircularProgress,
  Typography,
  Box,
} from "@mui/material";
import {
  Delete as DeleteIcon,
  Edit as EditIcon,
  Refresh as RefreshIcon,
  Schedule as ScheduleIcon,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  FactCheck as FactCheckIcon,
} from "@mui/icons-material";
import { useNavigate } from "react-router-dom";
import { TrackedPage } from "../../services/api";

// ✅ Updated props to match Dashboard
interface PageListProps {
  pages: TrackedPage[];
  onPageDeleted: (pageId: string) => void;
  onPageUpdated: (updatedPage: TrackedPage) => void;
  onPageCrawl: (pageId: string) => Promise<void>;
  crawlingPages: Set<string>; // ✅ New prop for loading states
}

const PageList: React.FC<PageListProps> = ({
  pages,
  onPageDeleted,
  onPageUpdated,
  onPageCrawl,
  crawlingPages,
}) => {
  const navigate = useNavigate();

  // ✅ Utility functions for formatting and status
  const formatDate = (dateString: string | null): string => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleString();
  };

  const formatTimeAgo = (dateString: string | null): string => {
    if (!dateString) return 'Never';
    
    const now = new Date();
    const date = new Date(dateString);
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);
    
    if (diffInSeconds < 60) return 'Just now';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
    return `${Math.floor(diffInSeconds / 86400)}d ago`;
  };

  const getStatusChip = (page: TrackedPage) => {
    if (!page.is_active) {
      return (
        <Chip 
          label="Inactive" 
          size="small" 
          color="default"
          icon={<WarningIcon />}
        />
      );
    }
    
    if (page.last_change_detected) {
      return (
        <Tooltip title={`Last change: ${formatDate(page.last_change_detected)}`}>
          <Chip 
            label="Changed" 
            size="small" 
            color="success"
            icon={<CheckCircleIcon />}
          />
        </Tooltip>
      );
    }
    
    if (page.last_checked) {
      return (
        <Chip 
          label="Monitored" 
          size="small" 
          color="primary"
          icon={<ScheduleIcon />}
        />
      );
    }
    
    return (
      <Chip 
        label="Pending" 
        size="small" 
        color="warning"
        icon={<ScheduleIcon />}
      />
    );
  };

  const truncateUrl = (url: string, maxLength: number = 50): string => {
    if (url.length <= maxLength) return url;
    return url.substring(0, maxLength) + '...';
  };

  // Check if a page has versions available for fact checking
  const hasVersionsForFactCheck = (page: TrackedPage): boolean => {
    // Pages with current_version_id have at least one version
    return !!page.current_version_id;
  };

  if (pages.length === 0) {
    return (
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="h6" color="text.secondary">
          No pages being monitored
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Add your first page to get started with monitoring!
        </Typography>
      </Paper>
    );
  }

  return (
    <TableContainer component={Paper} elevation={2}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell><strong>URL</strong></TableCell>
            <TableCell><strong>Display Name</strong></TableCell>
            <TableCell><strong>Status</strong></TableCell>
            <TableCell><strong>Last Checked</strong></TableCell>
            <TableCell><strong>Interval</strong></TableCell>
            <TableCell align="right"><strong>Actions</strong></TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {pages.map((page) => (
            <TableRow 
              key={page.id}
              sx={{
                '&:hover': {
                  backgroundColor: 'action.hover',
                },
                opacity: page.is_active ? 1 : 0.6,
              }}
            >
              {/* URL Column */}
              <TableCell>
                <Tooltip title={page.url}>
                  <Typography 
                    variant="body2" 
                    component="a"
                    href={page.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    sx={{
                      textDecoration: 'none',
                      color: 'primary.main',
                      '&:hover': {
                        textDecoration: 'underline',
                      },
                    }}
                  >
                    {truncateUrl(page.url)}
                  </Typography>
                </Tooltip>
              </TableCell>

              {/* Display Name Column */}
              <TableCell>
                <Typography variant="body2">
                  {page.display_name || truncateUrl(page.url, 30)}
                </Typography>
              </TableCell>

              {/* Status Column */}
              <TableCell>
                {getStatusChip(page)}
              </TableCell>

              {/* Last Checked Column */}
              <TableCell>
                <Box>
                  <Typography variant="body2">
                    {formatDate(page.last_checked)}
                  </Typography>
                  {page.last_checked && (
                    <Typography variant="caption" color="text.secondary">
                      {formatTimeAgo(page.last_checked)}
                    </Typography>
                  )}
                </Box>
              </TableCell>

              {/* Interval Column */}
              <TableCell>
                <Typography variant="body2">
                  {page.check_interval_minutes < 60
                    ? `${page.check_interval_minutes}m`
                    : page.check_interval_minutes < 1440
                    ? `${Math.round(page.check_interval_minutes / 60)}h`
                    : `${Math.round(page.check_interval_minutes / 1440)}d`
                  }
                </Typography>
              </TableCell>

              {/* Actions Column */}
              <TableCell align="right">
                {/* ✅ Enhanced Crawl Button with loading state */}
                <Tooltip title="Check for changes now">
                  <span>
                    <Button
                      variant="outlined"
                      size="small"
                      onClick={() => onPageCrawl(page.id)}
                      disabled={crawlingPages.has(page.id) || !page.is_active}
                      startIcon={
                        crawlingPages.has(page.id) ? (
                          <CircularProgress size={16} />
                        ) : (
                          <RefreshIcon />
                        )
                      }
                      sx={{ mr: 1, minWidth: '110px' }}
                    >
                      {crawlingPages.has(page.id) ? 'Checking...' : 'Check Now'}
                    </Button>
                  </span>
                </Tooltip>

                {/* ✅ Fact Check Button */}
                <Tooltip 
                  title={
                    hasVersionsForFactCheck(page) 
                      ? "Analyze content with fact checking" 
                      : "Check the page first to enable fact checking"
                  }
                >
                  <span>
                    <Button
                      variant="outlined"
                      size="small"
                      onClick={() => navigate(`/fact-check/${page.id}`)}
                      disabled={!hasVersionsForFactCheck(page)}
                      startIcon={<FactCheckIcon />}
                      sx={{ 
                        mr: 1,
                        minWidth: '100px',
                        borderColor: hasVersionsForFactCheck(page) ? 'primary.main' : 'grey.400',
                        color: hasVersionsForFactCheck(page) ? 'primary.main' : 'grey.400',
                        '&:hover': {
                          borderColor: hasVersionsForFactCheck(page) ? 'primary.dark' : 'grey.400',
                          backgroundColor: hasVersionsForFactCheck(page) ? 'primary.50' : 'transparent',
                        }
                      }}
                    >
                      Fact Check
                    </Button>
                  </span>
                </Tooltip>

                {/* Edit Button - placeholder for future functionality */}
                <Tooltip title="Edit page settings (coming soon)">
                  <span>
                    <IconButton
                      color="primary"
                      onClick={() => {
                        // TODO: Implement edit functionality
                        console.log('Edit page:', page.id);
                      }}
                      disabled
                      size="small"
                    >
                      <EditIcon />
                    </IconButton>
                  </span>
                </Tooltip>

                {/* Delete Button */}
                <Tooltip title="Delete this page">
                  <IconButton
                    color="error"
                    onClick={() => {
                      if (window.confirm(`Are you sure you want to delete monitoring for "${page.display_name || page.url}"?`)) {
                        onPageDeleted(page.id);
                      }
                    }}
                    size="small"
                  >
                    <DeleteIcon />
                  </IconButton>
                </Tooltip>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default PageList;