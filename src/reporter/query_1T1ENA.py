from exceptions.exceptions import AmbiguousNGSIIdError
from flask import request
from reporter.reporter import _validate_query_params
from translators.crate import CrateTranslatorInstance, CrateTranslator
import logging


def query_1T1ENA(entity_id,   # In Path
                 type_=None,  # In Query
                 attrs=None,
                 aggr_method=None,
                 aggr_period=None,
                 options=None,
                 from_date=None,
                 to_date=None,
                 last_n=None,
                 limit=10000,
                 offset=0):
    """
    See /entities/{entityId}/attrs/{attrName} in API Specification
    quantumleap.yml
    """
    r, c = _validate_query_params(aggr_period, aggr_method, attrs, options)
    if c != 200:
        return r, c

    if attrs is not None:
        attrs = attrs.split(',')

    fiware_s = request.headers.get('fiware-service', None)
    fiware_sp = request.headers.get('fiware-servicepath', None)

    entities = None
    try:
        with CrateTranslatorInstance() as trans:
            entities = trans.query(attr_names=attrs,
                               entity_type=type_,
                               entity_id=entity_id,
                               aggr_method=aggr_method,
                               from_date=from_date,
                               to_date=to_date,
                               last_n=last_n,
                               limit=limit,
                               offset=offset,
                               fiware_service=fiware_s,
                               fiware_servicepath=fiware_sp,)
    except AmbiguousNGSIIdError as e:
        return {
            "error": "AmbiguousNGSIIdError",
            "description": str(e)
        }, 409

    except Exception as e:
        # Temp workaround to debug test_not_found
        msg = "Something went wrong with QL. Error: {}".format(e)
        logging.getLogger().error(msg, exc_info=True)
        return msg, 500

    if entities:
        if aggr_method:
            index = []
        else:
            index = [str(e[CrateTranslator.TIME_INDEX_NAME]) for e in entities]

        ignore = ('type', 'id', CrateTranslator.TIME_INDEX_NAME)
        attrs = [at for at in sorted(entities[0].keys()) if at not in ignore]

        attributes = []
        for at in attrs:
            attributes.append({
                'attrName': at,
                'values': []
            })

        for i, at in enumerate(attrs):
            for e in entities:
                attributes[i]['values'].append(e[at]['value'])

        res = {
            'data': {
                'entityId': entity_id,
                'index': index,
                'attributes': attributes
            }
        }
        return res

    r = {
        "error": "Not Found",
        "description": "No records were found for such query."
    }
    return r, 404


def query_1T1ENA_value(*args, **kwargs):
    res = query_1T1ENA(*args, **kwargs)
    if isinstance(res, dict) and 'data' in res:
        res['data'].pop('entityId')
    return res
