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
import { useCallback, useEffect, useMemo, useState } from 'react';
import rison from 'rison';
import { t, SupersetClient } from '@superset-ui/core';
import { useListViewResource } from 'src/views/CRUD/hooks';
import withToasts from 'src/components/MessageToasts/withToasts';
import SubMenu, { SubMenuProps } from 'src/features/home/SubMenu';
import {
  FormModal,
  FormItem,
  AsyncSelect,
  Icons,
  Switch,
  Tooltip,
} from '@superset-ui/core/components';
import { ModalTitleWithIcon } from 'src/components/ModalTitleWithIcon';
import {
  ListView,
  ListViewActionsBar,
  type ListViewActionProps,
  type ListViewFilters,
} from 'src/components';

const RESOURCE = 'guest_rls_exempt_dataset';
const STRICT_MODE_ENDPOINT = '/api/v1/guest_rls_strict_mode/';

type StrictMode = {
  value: boolean;
  source: 'database' | 'environment';
  environment_default: boolean;
};

/**
 * The instance-wide strict-mode switch.
 *
 * Saving writes the choice to the database, and from then on it wins over the
 * GUEST_RLS_STRICT environment variable, so a restart does not revert it.
 * An embedding host can still override it for its own viewers by minting the
 * guest token with an `rls_strict` claim.
 */
function StrictModeToggle({
  addDangerToast,
  addSuccessToast,
}: {
  addDangerToast: (msg: string) => void;
  addSuccessToast: (msg: string) => void;
}) {
  const [state, setState] = useState<StrictMode | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let stale = false;
    SupersetClient.get({ endpoint: STRICT_MODE_ENDPOINT })
      .then(({ json }) => {
        if (!stale) setState(json.result);
      })
      .catch(() => {
        if (!stale)
          addDangerToast(t('Could not read the strict mode setting.'));
      });
    return () => {
      stale = true;
    };
  }, [addDangerToast]);

  const handleChange = async (value: boolean) => {
    setSaving(true);
    try {
      const { json } = await SupersetClient.put({
        endpoint: STRICT_MODE_ENDPOINT,
        jsonPayload: { value },
      });
      setState(prev => (prev ? { ...prev, ...json.result } : prev));
      addSuccessToast(
        value
          ? t('Strict mode on: guests without a clause get no rows.')
          : t('Strict mode off: guests without a clause see every row.'),
      );
    } catch {
      addDangerToast(t('Could not save the strict mode setting.'));
    } finally {
      setSaving(false);
    }
  };

  if (!state) {
    return null;
  }

  return (
    <Tooltip
      title={
        state.source === 'environment'
          ? // Two whole sentences rather than interpolating a translated "on":
            // a lone word carries no context for a translator.
            state.environment_default
            ? t(
                'Currently from GUEST_RLS_STRICT, which defaults to on. Saving ' +
                  'stores the choice in the database, which then takes precedence.',
              )
            : t(
                'Currently from GUEST_RLS_STRICT, which defaults to off. Saving ' +
                  'stores the choice in the database, which then takes precedence.',
              )
          : t(
              'Saved in the database, so it survives a restart and overrides ' +
                'GUEST_RLS_STRICT.',
            )
      }
    >
      <span>
        <Switch
          checked={state.value}
          loading={saving}
          onChange={handleChange}
          aria-label={t('Strict mode')}
        />{' '}
        {t('Strict mode')}
      </span>
    </Tooltip>
  );
}

type ExemptObject = {
  id: number;
  dataset?: { id: number; table_name: string };
};

interface Props {
  addDangerToast: (msg: string) => void;
  addSuccessToast: (msg: string) => void;
}

interface ExemptModalProps {
  show: boolean;
  onHide: () => void;
  onSave: () => void;
  addDangerToast: (msg: string) => void;
  addSuccessToast: (msg: string) => void;
}

// Loader for the dataset picker — searches all datasets via the related endpoint.
const loadDatasetOptions = (input = '', page: number, pageSize: number) => {
  const query = rison.encode({ filter: input, page, page_size: pageSize });
  return SupersetClient.get({
    endpoint: `/api/v1/${RESOURCE}/related/dataset?q=${query}`,
  }).then(response => ({
    data: response.json.result.map((item: { value: number; text: string }) => ({
      label: item.text,
      value: item.value,
    })),
    totalCount: response.json.count,
  }));
};

function ExemptModal({
  show,
  onHide,
  onSave,
  addDangerToast,
  addSuccessToast,
}: ExemptModalProps) {
  const handleFormSubmit = async (values: {
    dataset: number | { value: number };
  }) => {
    // `AsyncSelect` always sets `labelInValue`, so the form holds the whole
    // option, `{ label, value, key }`. The related field on the API wants the
    // primary key on its own -- handing it the option makes SQLAlchemy try to
    // build a `SqlaTable(label=...)`.
    const { dataset } = values;
    const datasetId = typeof dataset === 'object' ? dataset?.value : dataset;
    try {
      await SupersetClient.post({
        endpoint: `/api/v1/${RESOURCE}/`,
        jsonPayload: { dataset: datasetId },
      });
      addSuccessToast(t('Exempt dataset added.'));
    } catch (err) {
      addDangerToast(
        t('This dataset is already exempt, or could not be saved.'),
      );
      throw err;
    }
  };

  return (
    <FormModal
      show={show}
      onHide={onHide}
      name="add-exempt-dataset"
      title={
        <ModalTitleWithIcon
          title={t('Add exempt dataset')}
          icon={<Icons.PlusOutlined />}
        />
      }
      onSave={onSave}
      formSubmitHandler={handleFormSubmit}
      requiredFields={['dataset']}
      initialValues={{}}
    >
      <FormItem
        name="dataset"
        label={t('Dataset')}
        rules={[{ required: true, message: t('Dataset is required') }]}
      >
        <AsyncSelect
          ariaLabel={t('Dataset')}
          placeholder={t('Select a dataset')}
          options={loadDatasetOptions}
          getPopupContainer={trigger =>
            trigger.closest('.ant-modal-content') as HTMLElement
          }
        />
      </FormItem>
    </FormModal>
  );
}

function GuestRlsExemptDatasetList({ addDangerToast, addSuccessToast }: Props) {
  const {
    state: { loading, resourceCount, resourceCollection },
    fetchData,
    refreshData,
  } = useListViewResource<ExemptObject>(
    RESOURCE,
    t('exempt dataset'),
    addDangerToast,
  );

  const [showModal, setShowModal] = useState(false);

  const handleDelete = useCallback(
    async (row: ExemptObject) => {
      try {
        await SupersetClient.delete({
          endpoint: `/api/v1/${RESOURCE}/${row.id}`,
        });
        refreshData();
        addSuccessToast(t('Removed exempt dataset'));
      } catch (err) {
        addDangerToast(t('There was an issue removing the exempt dataset.'));
      }
    },
    [addDangerToast, addSuccessToast, refreshData],
  );

  const columns = useMemo(
    () => [
      {
        accessor: 'id',
        id: 'id',
        Header: 'ID',
        hidden: true,
      },
      {
        accessor: 'dataset.table_name',
        id: 'dataset',
        Header: t('Dataset'),
        disableSortBy: true,
        Cell: ({ row: { original } }: any) => (
          <span>{original.dataset?.table_name}</span>
        ),
      },
      {
        Cell: ({ row: { original } }: any) => {
          const actions = [
            {
              label: 'delete-action',
              tooltip: t('Remove'),
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

  const filters: ListViewFilters = useMemo(() => [], []);

  const subMenuButtons: SubMenuProps['buttons'] = [
    {
      name: (
        <>
          <Icons.PlusOutlined iconSize="m" /> {t('Exempt dataset')}
        </>
      ),
      buttonStyle: 'primary',
      onClick: () => setShowModal(true),
    },
  ];

  return (
    <>
      <SubMenu name={t('Guest RLS Exempt Datasets')} buttons={subMenuButtons} />
      <StrictModeToggle
        addDangerToast={addDangerToast}
        addSuccessToast={addSuccessToast}
      />
      <ExemptModal
        show={showModal}
        onHide={() => setShowModal(false)}
        onSave={() => {
          refreshData();
          setShowModal(false);
        }}
        addDangerToast={addDangerToast}
        addSuccessToast={addSuccessToast}
      />
      <ListView<ExemptObject>
        className="guest-rls-exempt-dataset-list-view"
        columns={columns}
        count={resourceCount}
        data={resourceCollection}
        fetchData={fetchData}
        refreshData={refreshData}
        filters={filters}
        initialSort={[{ id: 'id', desc: true }]}
        loading={loading}
        pageSize={25}
        addDangerToast={addDangerToast}
        addSuccessToast={addSuccessToast}
        emptyState={{
          title: t('No exempt datasets yet'),
          description: t(
            'Guests must carry an RLS clause for every dataset they query. ' +
              'Add shared/lookup datasets here so they are queryable without ' +
              'one (everything else returns no rows).',
          ),
          buttonText: (
            <>
              <Icons.PlusOutlined iconSize="m" /> {t('Exempt dataset')}
            </>
          ),
          buttonAction: () => setShowModal(true),
        }}
      />
    </>
  );
}

export default withToasts(GuestRlsExemptDatasetList);
