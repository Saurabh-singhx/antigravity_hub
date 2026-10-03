import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Linking,
  Alert,
  Platform,
} from 'react-native';
import { NeoColors, NeoStyles } from '../theme/neomorphism';
import NeoCard from './NeoCard';
import NeoPill from './NeoPill';

export default function QuestionButtonCard({ item, onToggleMastered }) {
  const [expanded, setExpanded] = useState(false);
  const [mastered, setMastered] = useState(Boolean(item.is_mastered));

  const handleToggle = () => {
    setExpanded((prev) => !prev);
  };

  const handleMasteredPress = () => {
    const nextVal = !mastered;
    setMastered(nextVal);
    if (onToggleMastered) {
      onToggleMastered(item.id, nextVal);
    }
  };

  const handleOpenSource = () => {
    const url = item.source?.source_url;
    if (url) {
      Linking.openURL(url).catch(() => {
        Alert.alert('Cannot Open URL', `Unable to open: ${url}`);
      });
    }
  };

  const getDifficultyColor = (diff) => {
    switch ((diff || '').toLowerCase()) {
      case 'easy':
        return '#059669'; // Green
      case 'hard':
        return '#dc2626'; // Red
      default:
        return '#d97706'; // Amber
    }
  };

  const getSlotPillInfo = (slotId) => {
    switch (slotId) {
      case 1:
        return { label: '🌅 Morning Fundamentals', color: '#0284c7' };
      case 2:
        return { label: '☀️ Afternoon Architecture', color: '#d97706' };
      case 3:
        return { label: '🌙 Evening Scenarios', color: '#7c3aed' };
      default:
        return { label: '🎯 Interview Prep', color: '#4f46e5' };
    }
  };

  const slotInfo = getSlotPillInfo(item.slot_id);
  const diffColor = getDifficultyColor(item.difficulty);

  return (
    <NeoCard style={styles.cardContainer}>
      {/* Top Header Row */}
      <View style={styles.headerRow}>
        <View style={styles.headerPills}>
          <NeoPill label={slotInfo.label} color={slotInfo.color} />
          <NeoPill label={item.category || 'Interview'} color="#475569" />
          <NeoPill label={item.difficulty || 'Medium'} color={diffColor} />
        </View>

        {mastered ? (
          <NeoPill label="✓ Mastered" color="#059669" bgColor="#d1fae5" />
        ) : null}
      </View>

      {/* Main Interactive Question Button */}
      <TouchableOpacity
        activeOpacity={0.82}
        onPress={handleToggle}
        style={[styles.questionButton, expanded && styles.questionButtonActive]}
      >
        <View style={styles.questionTextContainer}>
          <Text style={styles.questionPrefix}>Q:</Text>
          <Text style={styles.questionText}>{item.question}</Text>
        </View>

        <View style={styles.expandChevronContainer}>
          <Text style={styles.chevronText}>{expanded ? '▲ Hide' : '▼ View Answer'}</Text>
        </View>
      </TouchableOpacity>

      {/* Target Job Role Subtitle */}
      {item.job_title ? (
        <View style={styles.jobRoleRow}>
          <Text style={styles.jobRoleText}>
            🎯 For Applied Role: <Text style={styles.jobRoleBold}>{item.job_title}</Text>
          </Text>
        </View>
      ) : null}

      {/* Expandable Sourced Answer Section */}
      {expanded ? (
        <View style={styles.answerSection}>
          <View style={styles.answerHeaderRow}>
            <Text style={styles.answerLabel}>💡 Sourced Answer:</Text>
          </View>

          <View style={styles.answerBox}>
            <Text style={styles.answerText}>{item.answer}</Text>
          </View>

          {/* Source Grounding & Anti-Hallucination Card */}
          {item.source ? (
            <View style={styles.sourceVerificationCard}>
              <View style={styles.sourceTitleRow}>
                <Text style={styles.sourceVerifiedBadge}>✓ Verified Authentic Source</Text>
                {item.source.stars ? (
                  <Text style={styles.starText}>★ {item.source.stars.toLocaleString()}</Text>
                ) : null}
              </View>

              <Text style={styles.sourceNameText}>
                📁 {item.source.source_name}
              </Text>

              {item.source.source_quote ? (
                <View style={styles.quoteBox}>
                  <Text style={styles.quoteTitle}>Citation Excerpt:</Text>
                  <Text style={styles.quoteText}>"{item.source.source_quote}"</Text>
                </View>
              ) : null}

              {item.source.source_url ? (
                <TouchableOpacity onPress={handleOpenSource} style={styles.openSourceBtn}>
                  <Text style={styles.openSourceText}>🔗 Open Original Source Repo</Text>
                </TouchableOpacity>
              ) : null}
            </View>
          ) : null}

          {/* Tech Stack Pills */}
          {item.tech_stack && item.tech_stack.length > 0 ? (
            <View style={styles.techStackRow}>
              {item.tech_stack.map((tag, idx) => (
                <View key={idx} style={styles.techChip}>
                  <Text style={styles.techChipText}>#{tag}</Text>
                </View>
              ))}
            </View>
          ) : null}

          {/* Action Row */}
          <View style={styles.actionRow}>
            <TouchableOpacity
              onPress={handleMasteredPress}
              style={[
                styles.actionBtn,
                mastered ? styles.actionBtnMastered : styles.actionBtnDefault,
              ]}
            >
              <Text
                style={[
                  styles.actionBtnText,
                  mastered && { color: '#059669', fontWeight: 'bold' },
                ]}
              >
                {mastered ? '✓ Mastered' : '○ Mark as Mastered'}
              </Text>
            </TouchableOpacity>

            <TouchableOpacity onPress={handleToggle} style={styles.collapseBtn}>
              <Text style={styles.collapseBtnText}>▲ Collapse</Text>
            </TouchableOpacity>
          </View>
        </View>
      ) : null}
    </NeoCard>
  );
}

const styles = StyleSheet.create({
  cardContainer: {
    padding: 12,
    marginBottom: 14,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  headerPills: {
    flexDirection: 'row',
    gap: 6,
    flexWrap: 'wrap',
    alignItems: 'center',
  },
  questionButton: {
    backgroundColor: '#ebf1f8',
    borderRadius: 12,
    padding: 12,
    borderWidth: 1,
    borderTopColor: '#ffffff',
    borderLeftColor: '#ffffff',
    borderBottomColor: '#c5d2e3',
    borderRightColor: '#c5d2e3',
    ...Platform.select({
      ios: {
        shadowColor: '#96a7be',
        shadowOffset: { width: 3, height: 3 },
        shadowOpacity: 0.45,
        shadowRadius: 5,
      },
      android: {
        elevation: 3,
      },
      web: {
        boxShadow: '3px 3px 7px #cad6e6, -3px -3px 7px #ffffff',
      },
    }),
  },
  questionButtonActive: {
    backgroundColor: '#e1eaf5',
    borderColor: '#b4c5dc',
  },
  questionTextContainer: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  questionPrefix: {
    fontSize: 16,
    fontWeight: '900',
    color: '#4f46e5',
    marginRight: 6,
    lineHeight: 22,
  },
  questionText: {
    flex: 1,
    fontSize: 14,
    fontWeight: '700',
    color: NeoColors.textPrimary,
    lineHeight: 20,
  },
  expandChevronContainer: {
    marginTop: 8,
    alignSelf: 'flex-end',
    backgroundColor: 'rgba(79, 70, 229, 0.08)',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  chevronText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#4f46e5',
  },
  jobRoleRow: {
    marginTop: 8,
    paddingHorizontal: 4,
  },
  jobRoleText: {
    fontSize: 11,
    color: NeoColors.textMuted,
  },
  jobRoleBold: {
    fontWeight: '700',
    color: NeoColors.textSecondary,
  },
  answerSection: {
    marginTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#d6e0ed',
    paddingTop: 12,
  },
  answerHeaderRow: {
    marginBottom: 6,
  },
  answerLabel: {
    fontSize: 12,
    fontWeight: '800',
    color: '#334155',
    letterSpacing: 0.3,
  },
  answerBox: {
    backgroundColor: '#f3f7fd',
    borderRadius: 10,
    padding: 12,
    borderWidth: 1,
    borderColor: '#dce5f2',
    marginBottom: 10,
  },
  answerText: {
    fontSize: 13,
    color: NeoColors.textPrimary,
    lineHeight: 19,
  },
  sourceVerificationCard: {
    backgroundColor: '#e8edf5',
    borderRadius: 10,
    padding: 10,
    borderWidth: 1,
    borderColor: '#cdd9e8',
    marginBottom: 10,
  },
  sourceTitleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  sourceVerifiedBadge: {
    fontSize: 10,
    fontWeight: '800',
    color: '#059669',
    textTransform: 'uppercase',
  },
  starText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#d97706',
  },
  sourceNameText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#1e293b',
    marginBottom: 4,
  },
  quoteBox: {
    backgroundColor: '#ffffff',
    padding: 8,
    borderRadius: 6,
    borderLeftWidth: 3,
    borderLeftColor: '#4f46e5',
    marginVertical: 4,
  },
  quoteTitle: {
    fontSize: 9,
    fontWeight: '700',
    color: '#64748b',
    marginBottom: 2,
    textTransform: 'uppercase',
  },
  quoteText: {
    fontSize: 11,
    fontStyle: 'italic',
    color: '#475569',
    lineHeight: 15,
  },
  openSourceBtn: {
    marginTop: 6,
    alignSelf: 'flex-start',
  },
  openSourceText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#2563eb',
    textDecorationLine: 'underline',
  },
  techStackRow: {
    flexDirection: 'row',
    gap: 6,
    flexWrap: 'wrap',
    marginBottom: 10,
  },
  techChip: {
    backgroundColor: '#dbe4f0',
    paddingHorizontal: 7,
    paddingVertical: 3,
    borderRadius: 6,
  },
  techChipText: {
    fontSize: 10,
    color: '#475569',
    fontWeight: '600',
  },
  actionRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 4,
  },
  actionBtn: {
    paddingVertical: 7,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderWidth: 1,
  },
  actionBtnDefault: {
    backgroundColor: '#e6ecf5',
    borderColor: '#c5d2e3',
  },
  actionBtnMastered: {
    backgroundColor: '#d1fae5',
    borderColor: '#a7f3d0',
  },
  actionBtnText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#475569',
  },
  collapseBtn: {
    paddingVertical: 7,
    paddingHorizontal: 10,
  },
  collapseBtnText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#64748b',
  },
});
