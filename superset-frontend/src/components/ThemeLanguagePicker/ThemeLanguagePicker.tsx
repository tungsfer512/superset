/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
import { styled } from '@superset-ui/core';
import { Languages } from 'src/features/home/LanguagePicker';
import getBootstrapData from 'src/utils/getBootstrapData';
import ThemePicker from './ThemePicker';
import LanguagePicker from './LanguagePicker';

const StyledContainer = styled.div`
  display: inline-flex;
  align-items: center;
`;

export interface ThemeLanguagePickerProps {
  className?: string;
  locale?: string;
  languages?: Languages;
  showThemePicker?: boolean;
  showLanguagePicker?: boolean;
  menuMode?: 'horizontal' | 'vertical';
  gap?: number;
}

export default function ThemeLanguagePicker({
  className,
  locale,
  languages,
  showThemePicker = true,
  showLanguagePicker,
  menuMode = 'horizontal',
  gap = 2,
}: ThemeLanguagePickerProps) {
  const common = getBootstrapData().common;
  const navbarRight = common.menu_data.navbar_right;
  const langFromQuery = new URLSearchParams(window.location.search).get('lang');
  const resolvedLangFromQuery =
    langFromQuery && /^[a-zA-Z]{2,8}(?:_[a-zA-Z]{2,8})?$/.test(langFromQuery)
      ? langFromQuery
      : undefined;
  const commonLocale = common.locale ? String(common.locale) : undefined;
  const resolvedLanguages = languages ?? navbarRight.languages;
  const resolvedLocale =
    locale ??
    resolvedLangFromQuery ??
    commonLocale ??
    navbarRight.locale ??
    Object.keys(resolvedLanguages)[0] ??
    'en';
  const shouldShowLanguagePicker =
    showLanguagePicker ?? navbarRight.show_language_picker;

  return (
    <StyledContainer className={className} style={{ gap: `${gap * 4}px` }}>
      {showThemePicker && <ThemePicker menuMode={menuMode} />}
      {shouldShowLanguagePicker && (
        <LanguagePicker
          menuMode={menuMode}
          locale={resolvedLocale}
          languages={resolvedLanguages}
        />
      )}
    </StyledContainer>
  );
}
