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
import { useCallback, useMemo, useState } from 'react';
import { t, SupersetClient } from '@superset-ui/core';
import { useListViewResource } from 'src/views/CRUD/hooks';
import withToasts from 'src/components/MessageToasts/withToasts';
import SubMenu, { SubMenuProps } from 'src/features/home/SubMenu';
import {
  FormModal,
  FormItem,
  Input,
  Select,
  Icons,
} from '@superset-ui/core/components';
import { ModalTitleWithIcon } from 'src/components/ModalTitleWithIcon';
import getBootstrapData from 'src/utils/getBootstrapData';
import {
  ListView,
  ListViewFilterOperator as FilterOperator,
  ListViewActionsBar,
  type ListViewActionProps,
  type ListViewFilters,
} from 'src/components';

const RESOURCE = 'translation_dictionary';

// Available languages, sourced from the same list as the navbar language picker.
const LANGUAGE_OPTIONS = Object.entries(
  getBootstrapData()?.common?.menu_data?.navbar_right?.languages || {},
).map(([code, meta]: [string, any]) => ({
  value: code,
  label: `${meta?.name || code} (${code})`,
}));

type EntryObject = {
  id: number;
  locale: string;
  msgid: string;
  msgstr: string;
  source?: string;
  updated_on?: string;
};

interface Props {
  addDangerToast: (msg: string) => void;
  addSuccessToast: (msg: string) => void;
}

interface EntryModalProps {
  show: boolean;
  onHide: () => void;
  onSave: () => void;
  entry?: EntryObject | null;
  addDangerToast: (msg: string) => void;
  addSuccessToast: (msg: string) => void;
}

function EntryModal({
  show,
  onHide,
  onSave,
  entry,
  addDangerToast,
  addSuccessToast,
}: EntryModalProps) {
  const isEdit = Boolean(entry);

  const handleFormSubmit = async (values: {
    locale: string;
    msgid: string;
    msgstr: string;
  }) => {
    const payload = {
      locale: values.locale?.trim(),
      msgid: values.msgid,
      msgstr: values.msgstr,
    };
    try {
      if (isEdit && entry) {
        await SupersetClient.put({
          endpoint: `/api/v1/${RESOURCE}/${entry.id}`,
          jsonPayload: payload,
        });
        addSuccessToast(t('Translation updated.'));
      } else {
        await SupersetClient.post({
          endpoint: `/api/v1/${RESOURCE}/`,
          jsonPayload: payload,
        });
        addSuccessToast(t('Translation added.'));
      }
    } catch (err) {
      addDangerToast(
        t('There was an issue saving the translation (duplicate key?).'),
      );
      throw err;
    }
  };

  const initialValues = isEdit
    ? { locale: entry?.locale, msgid: entry?.msgid, msgstr: entry?.msgstr }
    : {};

  return (
    <FormModal
      show={show}
      onHide={onHide}
      name={isEdit ? 'edit-translation' : 'add-translation'}
      title={
        <ModalTitleWithIcon
          title={isEdit ? t('Edit translation') : t('Add translation')}
          icon={isEdit ? <Icons.EditOutlined /> : <Icons.PlusOutlined />}
        />
      }
      onSave={onSave}
      formSubmitHandler={handleFormSubmit}
      requiredFields={['locale', 'msgid', 'msgstr']}
      initialValues={initialValues}
    >
      <>
        <FormItem
          name="locale"
          label={t('Language')}
          rules={[{ required: true, message: t('Language is required') }]}
        >
          <Select
            ariaLabel={t('Language')}
            placeholder={t('Select a language')}
            options={LANGUAGE_OPTIONS}
            getPopupContainer={trigger =>
              (trigger.closest('.ant-modal-content') as HTMLElement) ||
              document.body
            }
          />
        </FormItem>
        <FormItem
          name="msgid"
          label={t('Source text')}
          rules={[{ required: true, message: t('Source text is required') }]}
        >
          <Input.TextArea
            autoSize={{ minRows: 2, maxRows: 8 }}
            placeholder={t('Original text (chart name, label, markdown...)')}
          />
        </FormItem>
        <FormItem
          name="msgstr"
          label={t('Translation')}
          rules={[{ required: true, message: t('Translation is required') }]}
        >
          <Input.TextArea
            autoSize={{ minRows: 2, maxRows: 8 }}
            placeholder={t('Translated text')}
          />
        </FormItem>
      </>
    </FormModal>
  );
}

function TranslationDictionaryList({ addDangerToast, addSuccessToast }: Props) {
  const {
    state: { loading, resourceCount, resourceCollection },
    fetchData,
    refreshData,
  } = useListViewResource<EntryObject>(
    RESOURCE,
    t('translation'),
    addDangerToast,
  );

  const [showModal, setShowModal] = useState(false);
  const [currentEntry, setCurrentEntry] = useState<EntryObject | null>(null);

  const openAdd = () => {
    setCurrentEntry(null);
    setShowModal(true);
  };
  const openEdit = (entry: EntryObject) => {
    setCurrentEntry(entry);
    setShowModal(true);
  };

  const handleDelete = useCallback(
    async (entry: EntryObject) => {
      try {
        await SupersetClient.delete({
          endpoint: `/api/v1/${RESOURCE}/${entry.id}`,
        });
        refreshData();
        addSuccessToast(t('Deleted translation'));
      } catch (err) {
        addDangerToast(t('There was an issue deleting the translation.'));
      }
    },
    [addDangerToast, addSuccessToast, refreshData],
  );

  const syncFromFile = useCallback(async () => {
    try {
      const { json } = await SupersetClient.post({
        endpoint: `/api/v1/${RESOURCE}/sync_from_file`,
      });
      refreshData();
      addSuccessToast(
        t('Synced from files: %s entries added.', json?.added ?? 0),
      );
    } catch (err) {
      addDangerToast(t('There was an issue syncing from files.'));
    }
  }, [addDangerToast, addSuccessToast, refreshData]);

  const exportToFile = useCallback(async () => {
    try {
      const { json } = await SupersetClient.post({
        endpoint: `/api/v1/${RESOURCE}/export_to_file`,
      });
      addSuccessToast(
        t('Exported to files: %s.', (json?.locales || []).join(', ') || '—'),
      );
    } catch (err) {
      addDangerToast(t('There was an issue exporting to files.'));
    }
  }, [addDangerToast, addSuccessToast]);

  const columns = useMemo(
    () => [
      {
        accessor: 'locale',
        id: 'locale',
        Header: t('Language'),
        size: 'sm',
      },
      {
        accessor: 'msgid',
        id: 'msgid',
        Header: t('Source text'),
        Cell: ({ row: { original } }: any) => <span>{original.msgid}</span>,
      },
      {
        accessor: 'msgstr',
        id: 'msgstr',
        Header: t('Translation'),
        Cell: ({ row: { original } }: any) => <span>{original.msgstr}</span>,
      },
      {
        accessor: 'source',
        id: 'source',
        Header: t('Source'),
        size: 'sm',
      },
      {
        Cell: ({ row: { original } }: any) => {
          const actions = [
            {
              label: 'edit-action',
              tooltip: t('Edit'),
              placement: 'bottom',
              icon: 'EditOutlined',
              onClick: () => openEdit(original),
            },
            {
              label: 'delete-action',
              tooltip: t('Delete'),
              placement: 'bottom',
              icon: 'DeleteOutlined',
              onClick: () => handleDelete(original),
            },
          ] as ListViewActionProps[];
          return <ListViewActionsBar actions={actions} />;
        },
        Header: t('Actions'),
        id: 'actions',
        hidden: false,
        disableSortBy: true,
        size: 'sm',
      },
    ],
    [handleDelete],
  );

  const filters: ListViewFilters = useMemo(
    () => [
      {
        Header: t('Language'),
        key: 'locale',
        id: 'locale',
        input: 'select',
        operator: FilterOperator.Equals,
        unfilteredLabel: t('All'),
        selects: LANGUAGE_OPTIONS,
      },
      {
        Header: t('Source text'),
        key: 'msgid',
        id: 'msgid',
        input: 'search',
        operator: FilterOperator.Contains,
      },
      {
        Header: t('Source'),
        key: 'source',
        id: 'source',
        input: 'select',
        operator: FilterOperator.Equals,
        unfilteredLabel: t('All'),
        selects: [
          { label: t('From file (po)'), value: 'po' },
          { label: t('Manual (db)'), value: 'db' },
        ],
      },
    ],
    [],
  );

  const subMenuButtons: SubMenuProps['buttons'] = [
    {
      name: t('Export to files'),
      buttonStyle: 'secondary',
      onClick: exportToFile,
    },
    {
      name: t('Sync from files'),
      buttonStyle: 'secondary',
      onClick: syncFromFile,
    },
    {
      name: (
        <>
          <Icons.PlusOutlined iconSize="m" /> {t('Translation')}
        </>
      ),
      buttonStyle: 'primary',
      onClick: openAdd,
    },
  ];

  return (
    <>
      <SubMenu name={t('Translation Dictionary')} buttons={subMenuButtons} />
      <EntryModal
        show={showModal}
        onHide={() => setShowModal(false)}
        onSave={() => {
          refreshData();
          setShowModal(false);
        }}
        entry={currentEntry}
        addDangerToast={addDangerToast}
        addSuccessToast={addSuccessToast}
      />
      <ListView<EntryObject>
        className="translation-dictionary-list-view"
        columns={columns}
        count={resourceCount}
        data={resourceCollection}
        fetchData={fetchData}
        refreshData={refreshData}
        filters={filters}
        initialSort={[{ id: 'updated_on', desc: true }]}
        loading={loading}
        pageSize={25}
        addDangerToast={addDangerToast}
        addSuccessToast={addSuccessToast}
        emptyState={{
          title: t('No translations yet'),
          description: t(
            'Add entries manually, or use "Sync from files" to import ' +
              'translations from the bundled po/mo files.',
          ),
          buttonText: (
            <>
              <Icons.PlusOutlined iconSize="m" /> {t('Translation')}
            </>
          ),
          buttonAction: openAdd,
        }}
      />
    </>
  );
}

export default withToasts(TranslationDictionaryList);
